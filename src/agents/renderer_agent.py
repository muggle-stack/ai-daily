"""Agent 4: HTML 渲染（暖调卡片风格）。使用 Python 模板，不使用 LLM。"""

import html
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone

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


def _collect_all_keywords(articles: list[ScoredArticle], limit: int = 15) -> list[str]:
    """收集所有文章的关键词，按出现频率排序，限制数量。"""
    counter: Counter[str] = Counter()
    original_case: dict[str, str] = {}
    for a in articles:
        for kw in a.keywords:
            kw_lower = kw.lower()
            counter[kw_lower] += 1
            if kw_lower not in original_case:
                original_case[kw_lower] = kw
    # 按频率降序，取前 limit 个
    return [original_case[kw] for kw, _ in counter.most_common(limit)]


def _format_publish_time(published: object) -> str:
    """格式化发布时间为友好显示。"""
    if not isinstance(published, datetime):
        return ""
    try:
        now = datetime.now(timezone.utc)
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        delta = now - published
        hours = delta.total_seconds() / 3600
        if hours < 1:
            return f"{int(delta.total_seconds() / 60)}分钟前"
        if hours < 24:
            return f"{int(hours)}小时前"
        if hours < 48:
            return "昨天"
        return published.strftime("%m-%d %H:%M")
    except Exception:
        return ""


def _build_article_card(
    article: ScoredArticle,
    summary_text: str,
    color: str,
    icon: str,
    rank: int,
) -> str:
    """构建单篇文章的 HTML 卡片。"""
    tags_html = " ".join(
        f'<span class="inline-block bg-warm-100 text-warm-600 text-xs px-2 py-0.5 rounded-full">{html.escape(kw)}</span>' for kw in article.keywords[:5]
    )

    # 摘要处理：优先用 writer 生成的摘要，fallback 到 article.summary
    if summary_text:
        summary_html = html.escape(summary_text)
    elif article.summary:
        summary_html = html.escape(article.summary[:300])
    else:
        summary_html = '<span class="empty-summary">点击查看原文</span>'

    # 分数显示
    score_str = f"{article.composite_score:.1f}"

    # 发布时间
    publish_time = _format_publish_time(article.published)

    # 精选样式（Top 3）
    is_featured = rank <= 3
    featured_class = ""
    featured_style = f"border-left: 4px solid {color};" if is_featured else ""

    return ARTICLE_CARD_TEMPLATE.format(
        title=html.escape(article.title),
        summary=summary_html,
        url=html.escape(article.url, quote=True),
        source=html.escape(article.source),
        tags=tags_html,
        color=color,
        icon=icon,
        score=score_str,
        publish_time=publish_time,
        featured_class=featured_class,
        featured_style=featured_style,
    )


def _extract_article_summaries(markdown: str) -> dict[str, str]:
    """从 Markdown 中提取每篇文章的摘要，以标题为 key。

    同时以中文标题和括号内英文原标题为 key 存储，提升匹配率。
    """
    summaries: dict[str, str] = {}
    lines = markdown.split("\n")
    current_title = ""
    current_en_title = ""
    current_summary_lines: list[str] = []

    def _save():
        if current_title and current_summary_lines:
            text = " ".join(current_summary_lines).strip()
            summaries[current_title] = text
            if current_en_title:
                summaries[current_en_title] = text

    for line in lines:
        if line.startswith("### "):
            _save()
            raw_title = line[4:].strip()
            # 提取括号中的英文原标题
            match = re.match(r"^(.+?)(?:（(.+?)）)?$", raw_title)
            if match:
                current_title = match.group(1).strip()
                current_en_title = (match.group(2) or "").strip()
            else:
                current_title = raw_title
                current_en_title = ""
            current_summary_lines = []
        elif line.startswith("🔗") or line.startswith("---") or line.startswith("## ") or line.startswith("# "):
            _save()
            current_title = ""
            current_en_title = ""
            current_summary_lines = []
        elif current_title and line.strip() and not line.startswith(">"):
            current_summary_lines.append(line.strip())

    _save()
    return summaries


def _find_summary_for_article(article: ScoredArticle, summaries: dict[str, str]) -> str:
    """为文章匹配 Markdown 中的摘要。模糊匹配标题。"""
    title = article.title.strip()
    if title in summaries:
        return summaries[title]
    for key, val in summaries.items():
        if title[:20] in key or key[:20] in title:
            return val
    return ""


def _build_sections(articles: list[ScoredArticle]) -> list[dict]:
    """将文章按板块分组，生成首页概览用的 sections 数据。"""
    section_map = config.SECTION_MAP
    section_icons = config.SECTION_ICONS
    section_order = config.SECTION_ORDER

    buckets: dict[str, list[dict]] = defaultdict(list)
    for a in articles:
        section_name = section_map.get(a.category, "行业动态")
        if len(buckets[section_name]) < 4:  # 每板块最多 4 条
            buckets[section_name].append({"title": a.title, "url": a.url})

    sections = []
    for name in section_order:
        items = buckets.get(name, [])
        if items:
            sections.append({
                "name": name,
                "icon": section_icons.get(name, "article"),
                "items": items,
            })
    return sections


def render_html(markdown: str, articles: list[ScoredArticle]) -> str:
    """将 Markdown 日报和文章数据渲染为 HTML。"""
    logger.info("开始渲染 HTML（%d 篇文章）", len(articles))

    date_str = datetime.now().strftime("%Y年%m月%d日")
    overview = _extract_overview(markdown)
    summaries = _extract_article_summaries(markdown)

    # 构建全局排名映射（按 composite_score 排序后的位置）
    sorted_articles = sorted(articles, key=lambda a: a.composite_score, reverse=True)
    rank_map = {a.url: i + 1 for i, a in enumerate(sorted_articles)}

    # 按分类分组
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
        cat_articles = by_category[cat]
        cards_html = "\n".join(
            _build_article_card(
                a,
                _find_summary_for_article(a, summaries),
                color,
                icon,
                rank_map.get(a.url, 99),
            )
            for a in cat_articles
        )
        content_parts.append(CATEGORY_SECTION_TEMPLATE.format(
            icon=icon,
            color=color,
            category=html.escape(cat),
            cards=cards_html,
            count=len(cat_articles),
        ))

    # 关键词（频率排序，限制 15 个）
    all_keywords = _collect_all_keywords(articles, limit=15)
    keywords_html = " ".join(
        f'<span class="inline-block bg-warm-100 text-warm-600 text-xs px-2.5 py-1 rounded-full border border-warm-200">{html.escape(kw)}</span>' for kw in all_keywords
    )

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


def save_output(
    markdown: str,
    html_content: str,
    articles: list[ScoredArticle] | None = None,
    overview: str = "",
    date_str: str | None = None,
) -> tuple[str, str]:
    """保存报告到站点结构，更新首页索引。

    输出路径: output/reports/{date}.html + 更新 output/reports.js
    """
    from src.agents.site_builder import ensure_site_structure, update_reports_index

    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    output_dir = config.OUTPUT_DIR
    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    # 保存报告文件
    md_path = reports_dir / f"{date_str}.md"
    html_path = reports_dir / f"{date_str}.html"

    md_path.write_text(markdown, encoding="utf-8")
    html_path.write_text(html_content, encoding="utf-8")

    logger.info("报告已保存: %s, %s", md_path, html_path)

    # 确保站点结构（首页、reports.js 等）
    ensure_site_structure()

    # 更新报告索引
    if articles:
        date_cn = datetime.now().strftime("%Y年%m月%d日")
        categories = list({a.category for a in articles})
        tags = []
        for a in articles:
            tags.extend(a.keywords[:2])
        tags = list(dict.fromkeys(tags))[:8]

        # 构建板块数据（6 个细分类 → 4 个板块）
        sections = _build_sections(articles)

        update_reports_index(
            date=date_str,
            title=f"AI 日报 · {date_cn}",
            summary=overview or "今日 AI 领域要闻精选",
            article_count=len(articles),
            categories=categories,
            tags=tags,
            sections=sections,
        )

    return str(md_path), str(html_path)


if __name__ == "__main__":
    import sys

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

    html_output = render_html(md_content, [])
    html_path = md_file.with_suffix(".html")
    html_path.write_text(html_output, encoding="utf-8")
    print(f"HTML 已生成: {html_path}")
