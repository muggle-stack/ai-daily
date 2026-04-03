"""Agent 2: 多 Agent 并行筛选 — 4 个板块 Agent 各自评分，汇总排序。"""

import json
import re
import time
from dataclasses import dataclass, field

import anthropic

from src import config
from src.agents.prefilter import compute_personal_boost, prefilter
from src.agents.rss_agent import Article
from src.prompts.filter_prompt import SECTION_PROMPTS, build_filter_user_message
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ScoredArticle:
    """评分后的文章数据结构 — 四维评分体系。"""

    title: str
    url: str
    source: str
    published: object  # datetime
    summary: str = ""
    content: str = ""
    relevance: float = 0.0
    novelty: float = 0.0
    depth: float = 0.0
    source_credibility: float = 0.0
    composite_score: float = 0.0
    personal_boost: float = 0.0
    reject_reason: str = ""
    category: str = "行业观点"
    keywords: list[str] = field(default_factory=list)

    @staticmethod
    def from_article(article: Article, score_data: dict, personal_boost: float = 0.0) -> "ScoredArticle":
        """从 Article 和评分数据创建 ScoredArticle。"""
        relevance = float(score_data.get("relevance", 5))
        novelty = float(score_data.get("novelty", 5))
        depth = float(score_data.get("depth", 5))
        source_credibility = float(score_data.get("source_credibility", 5))
        reject_reason = score_data.get("reject_reason", "")

        w = config.SCORE_WEIGHTS
        composite = (
            relevance * w["relevance"]
            + novelty * w["novelty"]
            + depth * w["depth"]
            + source_credibility * w["source_credibility"]
        ) + personal_boost

        return ScoredArticle(
            title=article.title,
            url=article.url,
            source=article.source,
            published=article.published,
            summary=article.summary,
            content=article.content,
            relevance=relevance,
            novelty=novelty,
            depth=depth,
            source_credibility=source_credibility,
            composite_score=composite,
            personal_boost=personal_boost,
            reject_reason=reject_reason,
            category=score_data.get("category", "行业观点"),
            keywords=score_data.get("keywords", []),
        )


def _call_claude_with_retry(
    client: anthropic.Anthropic,
    system: str,
    user_message: str,
    max_tokens: int = 8192,
    max_retries: int = 2,
    delay: float = 5.0,
) -> str:
    """调用 Claude API，失败自动重试。"""
    for attempt in range(max_retries + 1):
        try:
            response = client.messages.create(
                model=config.CLAUDE_MODEL,
                max_tokens=max_tokens,
                temperature=0,
                system=system,
                messages=[{"role": "user", "content": user_message}],
            )
            return response.content[0].text
        except (anthropic.APIError, anthropic.APIConnectionError) as e:
            if attempt < max_retries:
                logger.warning("Claude API 调用失败（第 %d 次），%s 秒后重试: %s", attempt + 1, delay, e)
                time.sleep(delay)
            else:
                logger.error("Claude API 调用失败，已达最大重试次数: %s", e)
                raise


def _parse_json_response(text: str) -> list[dict]:
    """解析 Claude 返回的 JSON，容忍 markdown 代码块。"""
    cleaned = re.sub(r"```(?:json)?\s*", "", text)
    cleaned = cleaned.strip()

    try:
        result = json.loads(cleaned)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            pass

    logger.error("无法解析 Claude 返回的 JSON:\n%s", text[:500])
    return []


def _run_section_agent(
    client: anthropic.Anthropic,
    section_name: str,
    system_prompt: str,
    articles: list[Article],
) -> list[dict]:
    """单个板块 Agent：对分配到的文章进行评分。

    如果文章数量超过 50 篇，自动分批处理，批次间加 3s 延迟避免限流。
    """
    batch_size = 50
    all_scores: list[dict] = []

    for i in range(0, len(articles), batch_size):
        if i > 0:
            time.sleep(3)  # 批次间延迟
        batch = articles[i : i + batch_size]
        user_message = build_filter_user_message(batch)

        try:
            response_text = _call_claude_with_retry(client, system_prompt, user_message)
        except Exception as e:
            logger.error("[%s] 评分失败: %s", section_name, e)
            continue

        batch_scores = _parse_json_response(response_text)
        if batch_scores:
            all_scores.extend(batch_scores)
        else:
            logger.warning("[%s] 评分结果为空（%d 篇）", section_name, len(batch))

    logger.info("[%s] 完成: %d 篇输入 → %d 条评分", section_name, len(articles), len(all_scores))
    return all_scores


def filter_and_score(articles: list[Article]) -> list[ScoredArticle]:
    """三层筛选：预过滤 → 4 个板块 Agent 并行评分 → 汇总排序。

    每个板块 Agent 收到全部文章，各自筛选自己负责的分类。
    最终汇总去重（同一 URL 取最高分）并排序。
    """
    if not articles:
        logger.warning("没有文章需要评分")
        return []

    # Layer 1+2: 预过滤
    filtered = prefilter(articles)
    if not filtered:
        logger.warning("预过滤后没有文章")
        return []

    # 预计算个性化加分
    boost_map = {a.url: compute_personal_boost(a) for a in filtered}

    logger.info("启动 %d 个板块 Agent 串行评分（共 %d 篇文章）", len(SECTION_PROMPTS), len(filtered))

    # Layer 3: 4 个板块 Agent 串行评分（避免并发触发 API 限流）
    client = anthropic.Anthropic(**config.get_anthropic_client_kwargs())
    all_scores: list[dict] = []

    for idx, (section_name, prompt) in enumerate(SECTION_PROMPTS.items()):
        if idx > 0:
            time.sleep(3)  # Agent 间延迟避免限流
        try:
            scores = _run_section_agent(client, section_name, prompt, filtered)
            all_scores.extend(scores)
        except Exception as e:
            logger.error("[%s] Agent 异常: %s", section_name, e)

    if not all_scores:
        logger.error("所有板块 Agent 评分结果均为空")
        return []

    logger.info("汇总: %d 条评分结果", len(all_scores))

    # 按 URL 建立索引 + 去重（同一 URL 被多个 Agent 评分时取最高分）
    article_map = {a.url: a for a in filtered}
    best_scores: dict[str, dict] = {}

    for item in all_scores:
        url = item.get("url", "")
        if not url or url not in article_map:
            continue
        reject_reason = item.get("reject_reason", "")
        if reject_reason:
            logger.debug("Claude 拒绝: %s", reject_reason[:60])
            continue

        # 计算该评分的综合分
        w = config.SCORE_WEIGHTS
        score = (
            float(item.get("relevance", 0)) * w["relevance"]
            + float(item.get("novelty", 0)) * w["novelty"]
            + float(item.get("depth", 0)) * w["depth"]
            + float(item.get("source_credibility", 0)) * w["source_credibility"]
        )

        if url not in best_scores or score > best_scores[url]["_score"]:
            item["_score"] = score
            best_scores[url] = item

    # 构建 ScoredArticle 列表
    scored: list[ScoredArticle] = []
    for url, item in best_scores.items():
        article = article_map[url]
        boost = boost_map.get(url, 0.0)
        scored.append(ScoredArticle.from_article(article, item, personal_boost=boost))

    scored.sort(key=lambda a: a.composite_score, reverse=True)
    logger.info("评分完成: %d 篇文章（去重后）", len(scored))
    return scored


if __name__ == "__main__":
    from src.agents.rss_agent import fetch_all

    config.load()
    raw = fetch_all()
    if raw:
        scored = filter_and_score(raw)
        top = scored[: config.TOP_N]
        print(f"\nTOP {len(top)} 篇文章：\n")
        for a in top:
            boost_str = f" +{a.personal_boost}" if a.personal_boost > 0 else ""
            print(f"  [{a.composite_score:.1f}{boost_str}] [{a.category}] {a.title}")
            print(f"    R={a.relevance:.0f} N={a.novelty:.0f} D={a.depth:.0f} S={a.source_credibility:.0f}")
            print(f"    关键词: {', '.join(a.keywords)}\n")
