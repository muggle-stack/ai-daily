"""预过滤模块 — Layer 1 规则过滤 + Layer 2 语义去重 + 个性化加分。

在调用 Claude API（Layer 3）之前执行，降低成本并提高信噪比。
"""

import html as html_module
import re
from difflib import SequenceMatcher

from src import config
from src.agents.rss_agent import Article
from src.utils.logger import get_logger

logger = get_logger(__name__)


def strip_html_tags(text: str) -> str:
    """去除 HTML 标签并反转义 HTML 实体。"""
    if not text:
        return text
    # 先处理已转义的 HTML（如 &lt;p&gt;）
    text = html_module.unescape(text)
    # 去除 HTML 标签
    text = re.sub(r"<[^>]+>", "", text)
    # 压缩多余空白
    text = re.sub(r"\s+", " ", text).strip()
    return text


# AI 相关性关键词 — 标题或摘要中必须包含至少一个才通过 Layer 1
_AI_KEYWORDS = {
    # 核心术语
    "ai", "artificial intelligence", "人工智能",
    "ml", "machine learning", "机器学习",
    "deep learning", "深度学习",
    "llm", "large language model", "大模型", "大语言模型",
    "neural network", "神经网络",
    "nlp", "natural language", "自然语言",
    # 模型/公司
    "gpt", "claude", "gemini", "gemma", "llama", "mistral", "qwen",
    "openai", "anthropic", "deepmind", "hugging face", "huggingface",
    "meta ai", "cohere", "stability",
    # 技术
    "transformer", "diffusion", "embedding", "fine-tun", "rlhf", "rag",
    "prompt", "token", "inference", "training", "benchmark",
    "multimodal", "多模态", "vision language",
    "agent", "智能体", "agentic",
    "quantiz", "量化", "int4", "int8",
    # 应用
    "chatbot", "copilot", "code gen", "text to", "image gen",
    "tts", "asr", "speech", "语音",
    "aigc", "生成式",
    # 硬件/基础设施
    "gpu", "tpu", "npu", "cuda", "tensor core",
    "risc-v", "edge ai", "on-device", "端侧",
    # 安全/治理
    "ai safety", "alignment", "ai regulation", "ai policy",
    "ai act", "ai governance",
}


def _is_ai_related(text_lower: str) -> bool:
    """快速判断文本是否与 AI 相关。"""
    return any(kw in text_lower for kw in _AI_KEYWORDS)


def apply_rule_filter(articles: list[Article]) -> list[Article]:
    """Layer 1: 规则过滤 — HTML 清理、黑名单、最小长度、AI 相关性。

    Args:
        articles: 原始文章列表。

    Returns:
        过滤后的文章列表（summary/content 已清理 HTML）。
    """
    blacklist = [kw.lower() for kw in config.BLACKLIST_KEYWORDS]
    min_len = config.MIN_CONTENT_LENGTH
    result: list[Article] = []
    removed_blacklist = 0
    removed_short = 0
    removed_irrelevant = 0

    for article in articles:
        # HTML 清理（就地修改，后续所有环节看到的都是干净文本）
        article.summary = strip_html_tags(article.summary)
        article.content = strip_html_tags(article.content)

        # 黑名单关键词检查
        text_lower = (article.title + " " + article.summary).lower()
        if any(kw in text_lower for kw in blacklist):
            removed_blacklist += 1
            continue

        # 最小内容长度
        if len(article.title) + len(article.summary) < min_len:
            removed_short += 1
            continue

        # AI 相关性快速过滤 — 标题或摘要必须包含至少一个 AI 关键词
        if not _is_ai_related(text_lower):
            removed_irrelevant += 1
            continue

        result.append(article)

    logger.info(
        "Layer 1 规则过滤: 黑名单 -%d, 过短 -%d, 无关 -%d, 剩余 %d 篇",
        removed_blacklist, removed_short, removed_irrelevant, len(result),
    )
    return result


def _get_source_weight(source: str) -> int:
    """获取源的权重值。"""
    return config.SOURCE_WEIGHTS.get(source, config.DEFAULT_SOURCE_WEIGHT)


def _title_keywords(title: str) -> set[str]:
    """提取标题中 >3 字符的词作为关键词集合。"""
    words = re.findall(r"[a-zA-Z\u4e00-\u9fff]{2,}[\w.-]*", title.lower())
    return {w for w in words if len(w) > 3}


def apply_semantic_dedup(articles: list[Article]) -> list[Article]:
    """Layer 2: 语义去重 — 标题相似度 + 关键词重叠检测。

    按源权重降序排列，高权重源优先保留。
    相似度 > DEDUP_SIMILARITY_THRESHOLD 或关键词重叠 > 0.5 视为重复。

    Args:
        articles: 经过规则过滤的文章列表。

    Returns:
        去重后的文章列表。
    """
    threshold = config.DEDUP_SIMILARITY_THRESHOLD
    # 按源权重降序（高权重先被遍历，优先保留）
    sorted_articles = sorted(articles, key=lambda a: _get_source_weight(a.source), reverse=True)

    kept: list[Article] = []
    kept_titles: list[str] = []
    kept_keywords: list[set[str]] = []
    removed = 0

    for article in sorted_articles:
        title = article.title.strip()
        title_kw = _title_keywords(title)
        is_dup = False

        for i, kept_title in enumerate(kept_titles):
            # 标题相似度检查
            ratio = SequenceMatcher(None, title.lower(), kept_title.lower()).ratio()
            if ratio > threshold:
                logger.debug(
                    "语义去重 (相似度%.2f): '%s' ≈ '%s'",
                    ratio, title[:40], kept_title[:40],
                )
                is_dup = True
                break

            # 关键词重叠检查
            if title_kw and kept_keywords[i]:
                overlap = len(title_kw & kept_keywords[i])
                overlap_ratio = overlap / min(len(title_kw), len(kept_keywords[i]))
                if overlap_ratio > 0.5 and overlap >= 2:
                    logger.debug(
                        "语义去重 (关键词重叠%.2f): '%s' ≈ '%s'",
                        overlap_ratio, title[:40], kept_title[:40],
                    )
                    is_dup = True
                    break

        if is_dup:
            removed += 1
        else:
            kept.append(article)
            kept_titles.append(title)
            kept_keywords.append(title_kw)

    if removed:
        logger.info("Layer 2 语义去重: 移除 %d 篇重复, 剩余 %d 篇", removed, len(kept))
    return kept


def compute_personal_boost(article: Article) -> float:
    """计算个性化兴趣加分。

    匹配 PERSONAL_INTERESTS 中的任意关键词则返回加分值，否则 0。
    """
    text = (article.title + " " + article.summary).lower()
    keywords_str = " ".join(getattr(article, "keywords", []))
    text += " " + keywords_str.lower()

    for interest in config.PERSONAL_INTERESTS:
        if interest.lower() in text:
            return config.PERSONAL_INTEREST_BOOST
    return 0.0


def prefilter(articles: list[Article]) -> list[Article]:
    """执行 Layer 1 + Layer 2 预过滤流水线。

    Args:
        articles: RSS 抓取的原始文章列表。

    Returns:
        经过规则过滤和语义去重后的文章列表。
    """
    total = len(articles)
    logger.info("预过滤开始: %d 篇文章", total)

    # Layer 1: 规则过滤（黑名单、最小长度、HTML 清理）
    articles = apply_rule_filter(articles)

    # Layer 2: 语义去重
    articles = apply_semantic_dedup(articles)

    logger.info("预过滤完成: %d → %d 篇", total, len(articles))
    return articles


if __name__ == "__main__":
    from src.agents.rss_agent import fetch_all

    config.load()
    raw = fetch_all()
    print(f"\n原始抓取: {len(raw)} 篇\n")

    filtered = prefilter(raw)
    print(f"\n预过滤后: {len(filtered)} 篇\n")
    for a in filtered[:20]:
        boost = compute_personal_boost(a)
        boost_str = f" [+{boost}]" if boost > 0 else ""
        print(f"  [{a.source}]{boost_str} {a.title}")
