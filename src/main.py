"""AI Daily 主入口 — 编排所有 Agent 按顺序执行。"""

import argparse
import re
import sys
from datetime import datetime

from src import config
from src.agents import rss_agent, filter_agent, writer_agent, renderer_agent, feishu_agent
from src.utils.logger import get_logger

logger = get_logger(__name__)


def _extract_overview(markdown: str) -> str:
    """从 Markdown 中提取引用块综述。"""
    for line in markdown.split("\n"):
        line = line.strip()
        if line.startswith("> "):
            return line[2:].strip()
    return "今日 AI 领域要闻精选"


def main() -> None:
    """主流程：RSS 抓取 → AI 筛选 → 摘要生成 → HTML 渲染 → 飞书发布。"""
    parser = argparse.ArgumentParser(description="AI Daily Report Generator")
    parser.add_argument("--hours", type=int, default=48, help="抓取最近多少小时的文章（默认 48）")
    parser.add_argument("--top-n", type=int, default=None, help="保留 TOP N 篇文章（默认从配置读取）")
    args = parser.parse_args()

    # 加载配置
    config.load()
    top_n = args.top_n or config.TOP_N

    logger.info("=== AI Daily 开始运行 ===")
    logger.info("参数: hours=%d, top_n=%d", args.hours, top_n)

    # Step 1: RSS 抓取
    try:
        raw_articles = rss_agent.fetch_all(hours=args.hours)
        logger.info("Step 1 完成: 抓取到 %d 篇文章", len(raw_articles))
    except Exception as e:
        logger.error("RSS 抓取失败: %s", e)
        raw_articles = []

    if not raw_articles:
        logger.warning("没有抓取到任何文章，退出")
        return

    # Step 2: AI 筛选评分
    try:
        scored_articles = filter_agent.filter_and_score(raw_articles)
        top_articles = scored_articles[:top_n]
        logger.info("Step 2 完成: 筛选出 TOP %d 篇", len(top_articles))
    except Exception as e:
        logger.error("AI 筛选失败: %s", e)
        top_articles = []

    if not top_articles:
        logger.warning("筛选后没有文章，退出")
        return

    # Step 3: 摘要生成
    try:
        markdown_report = writer_agent.generate_report(top_articles)
        logger.info("Step 3 完成: 日报 Markdown 已生成（%d 字符）", len(markdown_report))
    except Exception as e:
        logger.error("摘要生成失败: %s", e)
        markdown_report = ""

    if not markdown_report:
        logger.warning("日报内容为空，退出")
        return

    # Step 4: HTML 渲染 + 保存
    html_report = ""
    try:
        html_report = renderer_agent.render_html(markdown_report, top_articles)
        md_path, html_path = renderer_agent.save_output(markdown_report, html_report)
        logger.info("Step 4 完成: 文件已保存 %s, %s", md_path, html_path)
    except Exception as e:
        logger.error("HTML 渲染或保存失败: %s", e)

    # Step 5: 飞书推送（创建在线文档 + 群通知）
    try:
        doc_url = feishu_agent.publish(markdown_report)
        logger.info("Step 5 完成: 飞书文档 %s", doc_url)

        overview = _extract_overview(markdown_report)
        date_str = datetime.now().strftime("%Y-%m-%d")
        html_url = f"{config.GITHUB_PAGES_URL}/ai-daily-{date_str}.html" if config.GITHUB_PAGES_URL else ""
        feishu_agent.send_group_notification(doc_url, top_articles, overview, html_url=html_url)
    except Exception as e:
        logger.error("飞书推送失败: %s", e)

    logger.info("=== AI Daily 运行完成 ===")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error("未捕获的异常: %s", e, exc_info=True)
        sys.exit(1)
