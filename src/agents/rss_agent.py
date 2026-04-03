"""Agent 1: RSS 抓取 + 去重。"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone

import feedparser
import requests

from src import config
from src.utils.logger import get_logger

logger = get_logger(__name__)

# 36氪 AI 关键词过滤
_AI_KEYWORDS = {
    "AI", "人工智能", "大模型", "LLM", "GPT", "Claude", "Gemini",
    "机器学习", "深度学习", "神经网络", "NLP", "自然语言", "AIGC",
    "生成式", "Transformer", "OpenAI", "Anthropic", "智能体", "Agent",
}


@dataclass
class Article:
    """RSS 文章数据结构。"""

    title: str
    url: str
    source: str
    published: datetime
    summary: str = ""
    content: str = ""


def _parse_published(entry: dict) -> datetime | None:
    """解析 feedparser entry 的发布时间。"""
    parsed = entry.get("published_parsed")
    if parsed:
        try:
            return datetime(*parsed[:6], tzinfo=timezone.utc)
        except (ValueError, TypeError):
            pass
    # 尝试 updated_parsed
    parsed = entry.get("updated_parsed")
    if parsed:
        try:
            return datetime(*parsed[:6], tzinfo=timezone.utc)
        except (ValueError, TypeError):
            pass
    return None


def _is_ai_related(title: str, summary: str) -> bool:
    """检查文章是否与 AI 相关（用于 36氪等泛科技源）。"""
    text = (title + " " + summary).upper()
    return any(kw.upper() in text for kw in _AI_KEYWORDS)


def _fetch_single_feed(name: str, url: str, hours: int) -> list[Article]:
    """抓取单个 RSS 源。

    Args:
        name: 源名称。
        url: RSS 地址。
        hours: 保留最近多少小时内的文章。

    Returns:
        Article 列表。
    """
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "AI-Daily-Bot/1.0"})
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
    except Exception as e:
        logger.warning("抓取 %s 失败: %s", name, e)
        return []

    now = datetime.now(timezone.utc)
    cutoff_seconds = hours * 3600
    articles: list[Article] = []

    for entry in feed.entries:
        published = _parse_published(entry)
        if not published:
            # 无发布时间的文章使用当前时间
            published = now

        age = (now - published).total_seconds()
        if age > cutoff_seconds or age < -3600:
            # 超过时间窗口或未来文章（时区偏移容错 1h）
            continue

        title = entry.get("title", "").strip()
        link = entry.get("link", "").strip()
        if not title or not link:
            continue

        summary = entry.get("summary", "") or entry.get("description", "") or ""
        content = ""
        if hasattr(entry, "content") and entry.content:
            content = entry.content[0].get("value", "")

        # 36氪需要过滤 AI 相关
        if "36kr" in url and not _is_ai_related(title, summary):
            continue

        articles.append(Article(
            title=title,
            url=link,
            source=name,
            published=published,
            summary=summary[:2000],
            content=content[:5000],
        ))

    logger.info("从 %s 抓取到 %d 篇文章", name, len(articles))
    return articles


def fetch_all(hours: int = 48) -> list[Article]:
    """并发抓取所有 RSS 源，去重并按时间排序。

    Args:
        hours: 保留最近多少小时内的文章，默认 48。

    Returns:
        去重并按发布时间倒序排列的 Article 列表。
    """
    feeds = config.get_feeds()
    logger.info("开始抓取 %d 个 RSS 源（时间窗口 %dh）", len(feeds), hours)

    all_articles: list[Article] = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(_fetch_single_feed, name, url, hours): name
            for name, url in feeds
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                result = future.result()
                all_articles.extend(result)
            except Exception as e:
                logger.warning("处理 %s 结果时出错: %s", name, e)

    # URL 去重
    seen_urls: set[str] = set()
    unique: list[Article] = []
    for article in all_articles:
        if article.url not in seen_urls:
            seen_urls.add(article.url)
            unique.append(article)

    # 按发布时间倒序
    unique.sort(key=lambda a: a.published, reverse=True)

    logger.info("抓取完成，共 %d 篇文章（去重后 %d 篇）", len(all_articles), len(unique))
    return unique


if __name__ == "__main__":
    articles = fetch_all()
    print(f"\n共抓取到 {len(articles)} 篇文章\n")
    for a in articles[:10]:
        print(f"  [{a.source}] {a.title}")
        print(f"    {a.url}")
        print(f"    {a.published.strftime('%Y-%m-%d %H:%M')}\n")
