"""Agent 3: AI 摘要生成 + 分类编排。"""

import time
from collections import defaultdict
from datetime import datetime

import anthropic

from src import config
from src.agents.filter_agent import ScoredArticle
from src.prompts.writer_prompt import WRITER_SYSTEM_PROMPT, build_writer_user_message
from src.utils.logger import get_logger

logger = get_logger(__name__)


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
                temperature=0.3,
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


def generate_report(articles: list[ScoredArticle], date_str: str | None = None) -> str:
    """为筛选后的文章生成结构化中文日报 Markdown。

    Args:
        articles: 评分后的文章列表。
        date_str: 日期字符串，默认为今天。

    Returns:
        完整的 Markdown 日报文本。
    """
    if not articles:
        logger.warning("没有文章需要生成摘要")
        return ""

    if not date_str:
        date_str = datetime.now().strftime("%Y年%m月%d日")

    # 按分类分组
    by_category: dict[str, list[ScoredArticle]] = defaultdict(list)
    for article in articles:
        by_category[article.category].append(article)

    logger.info("开始生成日报摘要（%d 篇文章，%d 个分类）", len(articles), len(by_category))

    client = anthropic.Anthropic(**config.get_anthropic_client_kwargs())
    user_message = build_writer_user_message(by_category, date_str)

    try:
        markdown = _call_claude_with_retry(client, WRITER_SYSTEM_PROMPT, user_message)
    except Exception as e:
        logger.error("摘要生成失败: %s", e)
        return ""

    logger.info("日报摘要生成完成，共 %d 字符", len(markdown))
    return markdown


if __name__ == "__main__":
    config.load()

    from src.agents.rss_agent import fetch_all
    from src.agents.filter_agent import filter_and_score

    raw = fetch_all()
    if raw:
        scored = filter_and_score(raw)
        top = scored[: config.TOP_N]
        if top:
            md = generate_report(top)
            print(md)
