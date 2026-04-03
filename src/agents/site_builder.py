"""站点结构管理 — 首页生成、报告索引维护。"""

import json
import re
from pathlib import Path

from src import config
from src.utils.logger import get_logger

logger = get_logger(__name__)


def ensure_site_structure() -> None:
    """确保 output/ 下的站点目录结构存在，首页不存在则生成。"""
    output = config.OUTPUT_DIR
    (output / "reports").mkdir(parents=True, exist_ok=True)
    (output / "assets").mkdir(parents=True, exist_ok=True)

    index_path = output / "index.html"
    if not index_path.exists():
        generate_index_html()
        logger.info("首页已生成: %s", index_path)

    reports_js = output / "reports.js"
    if not reports_js.exists():
        reports_js.write_text("const reportsData = [];\n", encoding="utf-8")
        logger.info("报告索引已初始化: %s", reports_js)


def update_reports_index(
    date: str,
    title: str,
    summary: str,
    article_count: int,
    categories: list[str],
    tags: list[str],
    sections: list[dict] | None = None,
) -> None:
    """在 reports.js 头部追加一条新报告元数据。

    Args:
        sections: 板块数据列表，每项 {"name", "icon", "items": [{"title", "url"}]}
    """
    reports_js = config.OUTPUT_DIR / "reports.js"

    # 读取现有数据
    existing: list[dict] = []
    if reports_js.exists():
        content = reports_js.read_text(encoding="utf-8")
        match = re.search(r"const reportsData = (\[.*\]);", content, re.DOTALL)
        if match:
            try:
                existing = json.loads(match.group(1))
            except json.JSONDecodeError:
                logger.warning("reports.js 解析失败，将重建")

    new_entry = {
        "id": date,
        "title": title,
        "date": date,
        "summary": summary[:200],
        "articleCount": article_count,
        "categories": categories,
        "tags": tags[:8],
        "sections": sections or [],
    }

    # 去重：同日替换
    existing = [r for r in existing if r.get("id") != date]
    existing.insert(0, new_entry)

    # 写回
    js_content = "const reportsData = " + json.dumps(existing, ensure_ascii=False, indent=4) + ";\n"
    reports_js.write_text(js_content, encoding="utf-8")
    logger.info("报告索引已更新: %s (%d 条)", date, len(existing))


def generate_index_html() -> None:
    """生成首页 index.html — 暖调主题，JS 动态加载报告列表。"""
    from src.prompts.renderer_prompt import INDEX_PAGE_TEMPLATE

    index_path = config.OUTPUT_DIR / "index.html"
    index_path.write_text(INDEX_PAGE_TEMPLATE, encoding="utf-8")
    logger.info("首页已写入: %s", index_path)
