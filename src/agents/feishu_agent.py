"""Agent 5: 飞书在线文档创建 + 群通知。"""

import json
import re
import time
from datetime import datetime
from urllib.parse import quote

import requests

from src import config
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Token 缓存
_token_cache: dict[str, object] = {"token": "", "expires_at": 0.0}


def _get_tenant_token() -> str:
    """获取飞书 tenant_access_token，带缓存。"""
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"]:
        return str(_token_cache["token"])

    url = f"{config.FEISHU_BASE_URL}/open-apis/auth/v3/tenant_access_token/internal/"
    payload = {
        "app_id": config.FEISHU_APP_ID,
        "app_secret": config.FEISHU_APP_SECRET,
    }

    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if data.get("code") != 0:
        raise RuntimeError(f"获取飞书 token 失败: {data.get('msg', '未知错误')}")

    token = data["tenant_access_token"]
    _token_cache["token"] = token
    _token_cache["expires_at"] = now + 7000  # 略小于 2h

    logger.info("飞书 tenant_access_token 已获取")
    return token


def _feishu_request(
    method: str,
    url: str,
    payload: dict | None = None,
    max_retries: int = 2,
    delay: float = 5.0,
) -> dict:
    """发送飞书 API 请求（JSON），带重试。"""
    token = _get_tenant_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }

    for attempt in range(max_retries + 1):
        try:
            if method.upper() == "POST":
                resp = requests.post(url, json=payload, headers=headers, timeout=30)
            else:
                resp = requests.get(url, headers=headers, timeout=30)

            data = resp.json()

            if resp.status_code != 200 or data.get("code") != 0:
                raise RuntimeError(
                    f"飞书 API 错误: status={resp.status_code}, code={data.get('code')}, msg={data.get('msg')}"
                )

            return data
        except Exception as e:
            if attempt < max_retries:
                logger.warning("飞书 API 调用失败（第 %d 次），%s 秒后重试: %s", attempt + 1, delay, e)
                time.sleep(delay)
            else:
                logger.error("飞书 API 调用失败，已达最大重试次数: %s", e)
                raise

    return {}  # 不会到达


# ===== Docx API: 创建在线文档并写入内容 =====


def _create_docx(title: str) -> str:
    """在指定文件夹创建飞书在线文档。

    Args:
        title: 文档标题。

    Returns:
        document_id。
    """
    url = f"{config.FEISHU_BASE_URL}/open-apis/docx/v1/documents"
    payload: dict = {"title": title}
    if config.FEISHU_FOLDER_TOKEN:
        payload["folder_token"] = config.FEISHU_FOLDER_TOKEN

    data = _feishu_request("POST", url, payload)
    document_id = data.get("data", {}).get("document", {}).get("document_id", "")
    logger.info("飞书在线文档已创建: document_id=%s", document_id)

    # 给指定用户授予编辑权限
    if config.FEISHU_DOC_OWNER_ID:
        _grant_doc_permission(document_id)

    return document_id


def _grant_doc_permission(document_id: str) -> None:
    """给配置的用户授予文档编辑权限。"""
    url = f"{config.FEISHU_BASE_URL}/open-apis/drive/v1/permissions/{document_id}/members?type=docx"
    payload = {
        "member_type": "openid",
        "member_id": config.FEISHU_DOC_OWNER_ID,
        "perm": "full_access",
    }
    try:
        _feishu_request("POST", url, payload)
        logger.info("已授权用户 %s 访问文档", config.FEISHU_DOC_OWNER_ID)
    except Exception as e:
        logger.warning("授权用户访问文档失败: %s", e)


def _text_run(content: str, bold: bool = False, italic: bool = False, link: str = "") -> dict:
    """构建飞书 text_run 元素。"""
    style: dict = {}
    if bold:
        style["bold"] = True
    if italic:
        style["italic"] = True
    if link:
        style["link"] = {"url": quote(link, safe=":/?#[]@!$&'()*+,;=-._~%")}

    return {
        "text_run": {
            "content": content,
            "text_element_style": style,
        }
    }


def _parse_inline(text: str) -> list[dict]:
    """解析行内格式（加粗、链接）为 text_run 列表。"""
    elements: list[dict] = []
    pattern = r"(\*\*(.+?)\*\*|\[(.+?)\]\((.+?)\))"
    last_end = 0

    for match in re.finditer(pattern, text):
        if match.start() > last_end:
            plain = text[last_end : match.start()]
            if plain:
                elements.append(_text_run(plain))

        if match.group(2):
            elements.append(_text_run(match.group(2), bold=True))
        elif match.group(3) and match.group(4):
            elements.append(_text_run(match.group(3), link=match.group(4)))

        last_end = match.end()

    if last_end < len(text):
        remaining = text[last_end:]
        if remaining:
            elements.append(_text_run(remaining))

    if not elements:
        elements.append(_text_run(text))

    return elements


def _md_to_feishu_blocks(markdown: str) -> list[dict]:
    """将 Markdown 转换为飞书文档 block 列表。

    支持：h1-h3、正文、引用（斜体文本）、分割线、链接、加粗。
    """
    blocks: list[dict] = []

    for line in markdown.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith("### "):
            blocks.append({
                "block_type": 5,
                "heading3": {"style": {}, "elements": _parse_inline(stripped[4:])},
            })
        elif stripped.startswith("## "):
            blocks.append({
                "block_type": 4,
                "heading2": {"style": {}, "elements": _parse_inline(stripped[3:])},
            })
        elif stripped.startswith("# "):
            blocks.append({
                "block_type": 3,
                "heading1": {"style": {}, "elements": _parse_inline(stripped[2:])},
            })
        elif stripped == "---":
            blocks.append({"block_type": 22, "divider": {}})
        elif stripped.startswith("> "):
            # 引用用斜体文本表示（callout 是容器 block，结构复杂）
            elements = [_text_run(t["text_run"]["content"],
                                  bold=t["text_run"]["text_element_style"].get("bold", False),
                                  italic=True,
                                  link=t["text_run"]["text_element_style"].get("link", {}).get("url", ""))
                        for t in _parse_inline(stripped[2:])]
            blocks.append({
                "block_type": 2,
                "text": {"style": {}, "elements": elements},
            })
        else:
            blocks.append({
                "block_type": 2,
                "text": {"style": {}, "elements": _parse_inline(stripped)},
            })

    return blocks


def _write_blocks(document_id: str, blocks: list[dict]) -> None:
    """将 block 列表写入飞书文档。分批写入，每批最多 50 个。"""
    if not blocks:
        return

    batch_size = 50
    for i in range(0, len(blocks), batch_size):
        batch = blocks[i : i + batch_size]
        url = f"{config.FEISHU_BASE_URL}/open-apis/docx/v1/documents/{document_id}/blocks/{document_id}/children"
        _feishu_request("POST", url, {"children": batch})
        logger.info("写入 %d 个 block（批次 %d）", len(batch), i // batch_size + 1)


# ===== 公共接口 =====


def publish(markdown: str) -> str:
    """创建飞书在线文档并写入 Markdown 内容。

    Args:
        markdown: Markdown 格式的日报内容。

    Returns:
        在线文档的访问 URL。
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    title = f"AI Daily · {date_str}"

    logger.info("开始创建飞书文档: %s", title)

    try:
        document_id = _create_docx(title)
    except Exception as e:
        logger.error("创建在线文档失败: %s", e)
        raise

    try:
        blocks = _md_to_feishu_blocks(markdown)
        _write_blocks(document_id, blocks)
    except Exception as e:
        logger.error("写入文档内容失败，尝试写入降级内容: %s", e)
        try:
            fallback_blocks = [
                {
                    "block_type": 2,
                    "text": {"style": {}, "elements": [_text_run("完整日报内容请查看 GitHub Pages 上的 HTML 版本。")]},
                },
            ]
            _write_blocks(document_id, fallback_blocks)
        except Exception as fallback_err:
            logger.error("降级写入也失败: %s", fallback_err)

    doc_url = f"{config.FEISHU_DOC_URL_PREFIX}/docx/{document_id}"
    logger.info("飞书文档创建完成: %s", doc_url)
    return doc_url


def send_group_notification(
    doc_url: str,
    articles: list,
    overview: str = "今日 AI 领域要闻精选",
    html_url: str = "",
) -> None:
    """发送飞书群卡片通知。

    Args:
        doc_url: 飞书在线文档 URL。
        articles: 文章列表（用于统计）。
        overview: 一句话综述。
        html_url: GitHub Pages HTML 页面 URL（可选）。
    """
    if not config.FEISHU_CHAT_ID:
        logger.info("未配置 FEISHU_CHAT_ID，跳过群通知")
        return

    date_str = datetime.now().strftime("%Y-%m-%d")
    categories = list({a.category for a in articles if hasattr(a, "category")})
    cat_text = "、".join(categories[:6]) if categories else "综合资讯"

    # 构建按钮列表
    actions: list[dict] = [
        {
            "tag": "button",
            "text": {"tag": "plain_text", "content": "📖 飞书文档"},
            "url": doc_url,
            "type": "primary",
        }
    ]
    if html_url:
        actions.append({
            "tag": "button",
            "text": {"tag": "plain_text", "content": "🌐 网页版"},
            "url": html_url,
            "type": "default",
        })

    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": f"🤖 AI Daily · {date_str}"},
            "template": "purple",
        },
        "elements": [
            {"tag": "markdown", "content": overview},
            {"tag": "markdown", "content": f"📰 共 {len(articles)} 篇精选，涵盖 {cat_text}"},
            {"tag": "action", "actions": actions},
        ],
    }

    url = f"{config.FEISHU_BASE_URL}/open-apis/im/v1/messages?receive_id_type=chat_id"
    payload = {
        "receive_id": config.FEISHU_CHAT_ID,
        "msg_type": "interactive",
        "content": json.dumps(card, ensure_ascii=False),
    }

    try:
        _feishu_request("POST", url, payload)
        logger.info("群通知已发送")
    except Exception as e:
        logger.error("群通知发送失败: %s", e)
