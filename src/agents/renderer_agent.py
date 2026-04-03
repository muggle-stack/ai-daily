"""Agent 4: HTML 渲染（暖调 Claude 卡片风格）。使用 Python 模板，不使用 LLM。"""

import html
import os
import re
from datetime import datetime

from src import config
from src.agents.filter_agent import ScoredArticle
from src.prompts.renderer_prompt import (
    ARTICLE_CARD_TEMPLATE,
    CATEGORY_COLOR_MAP,
    CATEGORY_EMOJI_MAP,
    CATEGORY_SECTION_TEMPLATE,
    HTML_TEMPLATE,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


def _extract_overview(markdown: str) -> str:
    """从 Markdown 中提取引用块综述。"""
    for line in markdown.split("\n"):
        line = line.strip()
        if line.startswith("> "):
            return html.escape(line[2:].strip())
    return "今日 AI 领域要闻精选"


def _collect_all_keywords(articles: list[ScoredArticle]) -> list[str]:
    """收集所有文章的关键词并去重。"""
    seen: set[str] = set()
    keywords: list[str] = []
    for a in articles:
        for kw in a.keywords:
            kw_lower = kw.lower()
            if kw_lower not in seen:
                seen.add(kw_lower)
                keywords.append(kw)
    return keywords


def _build_article_card(article: ScoredArticle, summary_text: str, color: str) -> str:
    """构建单篇文章的 HTML 卡片。"""
    tags_html = " ".join(
        f'<span class="tag">#{html.escape(kw)}</span>' for kw in article.keywords[:5]
    )
    return ARTICLE_CARD_TEMPLATE.format(
        title=html.escape(article.title),
        summary=html.escape(summary_text) if summary_text else html.escape(article.summary[:300]),
        url=html.escape(article.url, quote=True),
        source=html.escape(article.source),
        tags=tags_html,
        color=color,
    )


def _extract_article_summaries(markdown: str) -> dict[str, str]:
    """从 Markdown 中提取每篇文章的摘要，以标题为 key。

    尝试匹配 ### 标题后的文本段落。
    """
    summaries: dict[str, str] = {}
    lines = markdown.split("\n")
    current_title = ""
    current_summary_lines: list[str] = []

    for line in lines:
        if line.startswith("### "):
            # 保存上一篇
            if current_title and current_summary_lines:
                summaries[current_title] = " ".join(current_summary_lines).strip()
            current_title = line[4:].strip()
            # 去掉可能的括号中英文原标题
            match = re.match(r"^(.+?)(?:（.+?）)?$", current_title)
            if match:
                current_title = match.group(1).strip()
            current_summary_lines = []
        elif line.startswith("🔗") or line.startswith("---") or line.startswith("## ") or line.startswith("# "):
            # 摘要段落结束
            if current_title and current_summary_lines:
                summaries[current_title] = " ".join(current_summary_lines).strip()
                current_title = ""
                current_summary_lines = []
        elif current_title and line.strip() and not line.startswith(">"):
            current_summary_lines.append(line.strip())

    # 最后一篇
    if current_title and current_summary_lines:
        summaries[current_title] = " ".join(current_summary_lines).strip()

    return summaries


def _find_summary_for_article(article: ScoredArticle, summaries: dict[str, str]) -> str:
    """为文章匹配 Markdown 中的摘要。模糊匹配标题。"""
    title = article.title.strip()
    # 精确匹配
    if title in summaries:
        return summaries[title]
    # 包含匹配
    for key, val in summaries.items():
        if title[:20] in key or key[:20] in title:
            return val
    return ""


def render_html(markdown: str, articles: list[ScoredArticle]) -> str:
    """将 Markdown 日报和文章数据渲染为 HTML。

    Args:
        markdown: Claude 生成的 Markdown 日报。
        articles: 评分后的文章列表（用于结构化数据）。

    Returns:
        完整的 HTML 字符串。
    """
    logger.info("开始渲染 HTML（%d 篇文章）", len(articles))

    date_str = datetime.now().strftime("%Y年%m月%d日")
    overview = _extract_overview(markdown)
    summaries = _extract_article_summaries(markdown)

    # 按分类分组
    from collections import defaultdict
    by_category: dict[str, list[ScoredArticle]] = defaultdict(list)
    for a in articles:
        by_category[a.category].append(a)

    # 渲染分类区块
    content_parts: list[str] = []
    category_order = ["模型发布", "开源项目", "研究论文", "产品动态", "行业观点", "工具技巧"]
    for cat in category_order:
        if cat not in by_category:
            continue
        icon = CATEGORY_EMOJI_MAP.get(cat, "article")
        color = CATEGORY_COLOR_MAP.get(cat, "#c96442")
        cards_html = "\n".join(
            _build_article_card(a, _find_summary_for_article(a, summaries), color)
            for a in by_category[cat]
        )
        content_parts.append(CATEGORY_SECTION_TEMPLATE.format(
            icon=icon,
            color=color,
            category=html.escape(cat),
            cards=cards_html,
        ))

    # 关键词
    all_keywords = _collect_all_keywords(articles)
    keywords_html = " ".join(
        f'<span class="tag">#{html.escape(kw)}</span>' for kw in all_keywords[:30]
    )

    # 统计来源数
    sources = {a.source for a in articles}

    final_html = HTML_TEMPLATE.format(
        date=html.escape(date_str),
        article_count=len(articles),
        source_count=len(sources),
        overview=overview,
        content="\n".join(content_parts),
        keywords_html=keywords_html,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )

    logger.info("HTML 渲染完成")
    return final_html


def save_output(markdown: str, html_content: str, date_str: str | None = None) -> tuple[str, str]:
    """保存 Markdown 和 HTML 文件到 output 目录。

    Args:
        markdown: Markdown 内容。
        html_content: HTML 内容。
        date_str: 日期字符串（YYYY-MM-DD 格式），默认为今天。

    Returns:
        (markdown_path, html_path) 文件路径元组。
    """
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    output_dir = config.OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    md_path = output_dir / f"ai-daily-{date_str}.md"
    html_path = output_dir / f"ai-daily-{date_str}.html"

    md_path.write_text(markdown, encoding="utf-8")
    html_path.write_text(html_content, encoding="utf-8")

    logger.info("文件已保存: %s, %s", md_path, html_path)
    return str(md_path), str(html_path)


if __name__ == "__main__":
    import sys

    # 尝试读取最近的 Markdown 文件并渲染
    output_dir = config.OUTPUT_DIR
    if not output_dir.exists():
        print("output/ 目录不存在")
        sys.exit(1)

    md_files = sorted(output_dir.glob("ai-daily-*.md"), reverse=True)
    if not md_files:
        print("未找到 Markdown 文件")
        sys.exit(1)

    md_file = md_files[0]
    print(f"读取: {md_file}")
    md_content = md_file.read_text(encoding="utf-8")

    # 没有结构化数据时使用空列表
    html_output = render_html(md_content, [])
    html_path = md_file.with_suffix(".html")
    html_path.write_text(html_output, encoding="utf-8")
    print(f"HTML 已生成: {html_path}")
