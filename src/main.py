"""AI Daily 主入口 — 编排所有 Agent 按顺序执行。"""

import argparse
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


def run_pipeline(hours: int = 48, top_n: int | None = None, github_pages_url: str = "") -> dict:
    """运行完整 pipeline，返回结果字典。供 CLI 和 HTTP 服务调用。

    Args:
        hours: 抓取最近多少小时的文章
        top_n: 保留 TOP N 篇文章（None 则从配置读取）
        github_pages_url: GitHub Pages 基础 URL，用于飞书通知中的网页链接

    Returns:
        包含 pipeline 运行结果的字典
    """
    config.load()
    top_n = top_n or config.TOP_N
    date_str = datetime.now().strftime("%Y-%m-%d")

    result: dict = {
        "success": False,
        "date": date_str,
        "article_count": 0,
        "categories": [],
        "html_content": None,
        "md_content": None,
        "html_path": None,
        "md_path": None,
        "feishu_doc_url": None,
        "overview": None,
        "error": None,
    }

    logger.info("=== AI Daily 开始运行 ===")
    logger.info("参数: hours=%d, top_n=%d", hours, top_n)

    # Step 1: RSS 抓取
    try:
        raw_articles = rss_agent.fetch_all(hours=hours)
        logger.info("Step 1 完成: 抓取到 %d 篇文章", len(raw_articles))
    except Exception as e:
        logger.error("RSS 抓取失败: %s", e)
        result["error"] = f"RSS 抓取失败: {e}"
        return result

    if not raw_articles:
        logger.warning("没有抓取到任何文章，退出")
        result["error"] = "没有抓取到任何文章"
        return result

    # Step 2: AI 筛选评分
    try:
        scored_articles = filter_agent.filter_and_score(raw_articles)
        top_articles = scored_articles[:top_n]
        logger.info("Step 2 完成: 筛选出 TOP %d 篇", len(top_articles))
    except Exception as e:
        logger.error("AI 筛选失败: %s", e)
        result["error"] = f"AI 筛选失败: {e}"
        return result

    if not top_articles:
        logger.warning("筛选后没有文章，退出")
        result["error"] = "筛选后没有文章"
        return result

    result["article_count"] = len(top_articles)
    result["categories"] = list({a.category for a in top_articles})

    # Step 3: 摘要生成
    try:
        markdown_report = writer_agent.generate_report(top_articles)
        logger.info("Step 3 完成: 日报 Markdown 已生成（%d 字符）", len(markdown_report))
    except Exception as e:
        logger.error("摘要生成失败: %s", e)
        result["error"] = f"摘要生成失败: {e}"
        return result

    if not markdown_report:
        logger.warning("日报内容为空，退出")
        result["error"] = "日报内容为空"
        return result

    result["md_content"] = markdown_report
    result["overview"] = _extract_overview(markdown_report)

    # Step 4: HTML 渲染 + 保存
    try:
        html_report = renderer_agent.render_html(markdown_report, top_articles)
        md_path, html_path = renderer_agent.save_output(markdown_report, html_report)
        logger.info("Step 4 完成: 文件已保存 %s, %s", md_path, html_path)
        result["html_content"] = html_report
        result["html_path"] = html_path
        result["md_path"] = md_path
    except Exception as e:
        logger.error("HTML 渲染或保存失败: %s", e)
        result["error"] = f"HTML 渲染失败: {e}"
        return result

    # Step 5: 飞书推送（创建在线文档 + 群通知）
    try:
        doc_url = feishu_agent.publish(markdown_report)
        logger.info("Step 5 完成: 飞书文档 %s", doc_url)
        result["feishu_doc_url"] = doc_url

        overview = result["overview"]
        pages_url = github_pages_url or config.GITHUB_PAGES_URL
        html_url = f"{pages_url}/ai-daily-{date_str}.html" if pages_url else ""
        feishu_agent.send_group_notification(doc_url, top_articles, overview, html_url=html_url)
    except Exception as e:
        logger.error("飞书推送失败: %s", e)
        # 飞书失败不影响整体成功状态，pipeline 核心已完成

    result["success"] = True
    logger.info("=== AI Daily 运行完成 ===")
    return result


def main() -> None:
    """CLI 入口：解析命令行参数并调用 run_pipeline。"""
    parser = argparse.ArgumentParser(description="AI Daily Report Generator")
    parser.add_argument("--hours", type=int, default=48, help="抓取最近多少小时的文章（默认 48）")
    parser.add_argument("--top-n", type=int, default=None, help="保留 TOP N 篇文章（默认从配置读取）")
    args = parser.parse_args()

    result = run_pipeline(hours=args.hours, top_n=args.top_n)
    if not result["success"]:
        logger.error("Pipeline 失败: %s", result["error"])
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error("未捕获的异常: %s", e, exc_info=True)
        sys.exit(1)
