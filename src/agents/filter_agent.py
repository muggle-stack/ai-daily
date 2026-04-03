"""Agent 2: AI 智能筛选 + 评分。"""

import json
import re
import time
from dataclasses import dataclass, field

import anthropic

from src import config
from src.agents.rss_agent import Article
from src.prompts.filter_prompt import FILTER_SYSTEM_PROMPT, build_filter_user_message
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ScoredArticle:
    """评分后的文章数据结构。"""

    title: str
    url: str
    source: str
    published: object  # datetime
    summary: str = ""
    content: str = ""
    relevance: float = 0.0
    quality: float = 0.0
    timeliness: float = 0.0
    composite_score: float = 0.0
    category: str = "行业观点"
    keywords: list[str] = field(default_factory=list)

    @staticmethod
    def from_article(article: Article, score_data: dict) -> "ScoredArticle":
        """从 Article 和评分数据创建 ScoredArticle。"""
        relevance = float(score_data.get("relevance", 5))
        quality = float(score_data.get("quality", 5))
        timeliness = float(score_data.get("timeliness", 5))
        composite = relevance * 0.4 + quality * 0.35 + timeliness * 0.25

        return ScoredArticle(
            title=article.title,
            url=article.url,
            source=article.source,
            published=article.published,
            summary=article.summary,
            content=article.content,
            relevance=relevance,
            quality=quality,
            timeliness=timeliness,
            composite_score=composite,
            category=score_data.get("category", "行业观点"),
            keywords=score_data.get("keywords", []),
        )


def _call_claude_with_retry(
    client: anthropic.Anthropic,
    system: str,
    user_message: str,
    max_tokens: int = 4096,
    max_retries: int = 2,
    delay: float = 5.0,
) -> str:
    """调用 Claude API，失败自动重试。

    Args:
        client: Anthropic 客户端。
        system: 系统提示。
        user_message: 用户消息。
        max_tokens: 最大输出 token 数。
        max_retries: 最大重试次数。
        delay: 重试间隔（秒）。

    Returns:
        Claude 的回复文本。
    """
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
    # 去掉 markdown 代码块
    cleaned = re.sub(r"```(?:json)?\s*", "", text)
    cleaned = cleaned.strip()

    try:
        result = json.loads(cleaned)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    # 尝试提取第一个 [ 到最后一个 ] 之间的内容
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            pass

    logger.error("无法解析 Claude 返回的 JSON:\n%s", text[:500])
    return []


def filter_and_score(articles: list[Article]) -> list[ScoredArticle]:
    """调用 Claude 对文章进行评分和分类。

    Args:
        articles: 原始文章列表。

    Returns:
        评分后的文章列表，按综合分降序排列。
    """
    if not articles:
        logger.warning("没有文章需要评分")
        return []

    logger.info("开始对 %d 篇文章进行 AI 评分", len(articles))

    client = anthropic.Anthropic(**config.get_anthropic_client_kwargs())
    user_message = build_filter_user_message(articles)

    try:
        response_text = _call_claude_with_retry(client, FILTER_SYSTEM_PROMPT, user_message)
    except Exception as e:
        logger.error("筛选评分失败: %s", e)
        return []

    score_list = _parse_json_response(response_text)
    if not score_list:
        logger.error("评分结果为空")
        return []

    # 按 URL 建立索引
    article_map = {a.url: a for a in articles}
    scored: list[ScoredArticle] = []

    for item in score_list:
        url = item.get("url", "")
        article = article_map.get(url)
        if article:
            scored.append(ScoredArticle.from_article(article, item))
        else:
            logger.debug("评分结果中的 URL 未匹配: %s", url)

    scored.sort(key=lambda a: a.composite_score, reverse=True)
    logger.info("评分完成，%d 篇文章获得评分", len(scored))

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
            print(f"  [{a.composite_score:.1f}] [{a.category}] {a.title}")
            print(f"    关键词: {', '.join(a.keywords)}\n")
