"""统一配置管理，所有 API key 从环境变量读取。"""

import os
from pathlib import Path

from dotenv import load_dotenv

from src.utils.logger import get_logger

logger = get_logger(__name__)

# ===== 项目路径 =====
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"

# ===== 必填配置（调用 load() 后可用）=====
ANTHROPIC_API_KEY: str = ""
FEISHU_APP_ID: str = ""
FEISHU_APP_SECRET: str = ""
FEISHU_FOLDER_TOKEN: str = ""

# ===== 选填配置 =====
ANTHROPIC_BASE_URL: str = ""
ANTHROPIC_AUTH_TOKEN: str = ""
FEISHU_CHAT_ID: str = ""
FEISHU_DOC_OWNER_ID: str = ""
GITHUB_PAGES_URL: str = ""
FEISHU_BASE_URL: str = "https://open.feishu.cn"
FEISHU_DOC_URL_PREFIX: str = "https://feishu.cn"
CLAUDE_MODEL: str = "claude-sonnet-4-20250514"
TOP_N: int = 15
LOG_LEVEL: str = "INFO"

# ===== 默认 RSS 源 =====
DEFAULT_RSS_FEEDS: list[tuple[str, str]] = [
    ("smol.ai", "https://news.smol.ai/rss"),
    ("Hacker News", "https://hnrss.org/newest?q=AI+LLM+GPT+Claude&count=30"),
    ("Reddit ML", "https://www.reddit.com/r/MachineLearning/.rss"),
    ("Google AI Blog", "https://blog.google/technology/ai/rss/"),
    ("OpenAI Blog", "https://openai.com/blog/rss.xml"),
    ("Anthropic Blog", "https://www.anthropic.com/rss.xml"),
    ("HuggingFace Blog", "https://huggingface.co/blog/feed.xml"),
    ("Simon Willison", "https://simonwillison.net/atom/everything/"),
    ("机器之心", "https://www.jiqizhixin.com/rss"),
    ("36氪", "https://www.36kr.com/feed"),
]

RSS_FEEDS: list[tuple[str, str]] = []

_loaded = False


def load() -> None:
    """加载并校验必填环境变量。在 main.py 启动时调用。"""
    global ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, ANTHROPIC_AUTH_TOKEN
    global FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_FOLDER_TOKEN
    global FEISHU_CHAT_ID, FEISHU_DOC_OWNER_ID, FEISHU_BASE_URL, FEISHU_DOC_URL_PREFIX
    global GITHUB_PAGES_URL
    global CLAUDE_MODEL, TOP_N, LOG_LEVEL
    global RSS_FEEDS, _loaded

    if _loaded:
        return

    # 加载 .env 文件
    load_dotenv(PROJECT_ROOT / ".env", override=True)

    # 清理空字符串的环境变量，防止 SDK 误读空值作为有效凭证
    for key in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL"):
        if os.environ.get(key) == "":
            del os.environ[key]

    # 必填
    required = [
        "FEISHU_APP_ID",
        "FEISHU_APP_SECRET",
    ]
    missing = [k for k in required if not os.environ.get(k)]
    # ANTHROPIC_API_KEY 或 ANTHROPIC_AUTH_TOKEN 至少需要一个
    if not os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        missing.append("ANTHROPIC_API_KEY 或 ANTHROPIC_AUTH_TOKEN")
    if missing:
        raise ValueError(f"缺少必填环境变量: {', '.join(missing)}")

    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
    ANTHROPIC_BASE_URL = os.environ.get("ANTHROPIC_BASE_URL", "")
    ANTHROPIC_AUTH_TOKEN = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
    FEISHU_APP_ID = os.environ["FEISHU_APP_ID"]
    FEISHU_APP_SECRET = os.environ["FEISHU_APP_SECRET"]
    FEISHU_FOLDER_TOKEN = os.environ.get("FEISHU_FOLDER_TOKEN", "")

    # 选填
    FEISHU_CHAT_ID = os.environ.get("FEISHU_CHAT_ID", "")
    FEISHU_DOC_OWNER_ID = os.environ.get("FEISHU_DOC_OWNER_ID", "")
    FEISHU_BASE_URL = os.environ.get("FEISHU_BASE_URL", "https://open.feishu.cn")
    FEISHU_DOC_URL_PREFIX = os.environ.get("FEISHU_DOC_URL_PREFIX", "https://feishu.cn")
    GITHUB_PAGES_URL = os.environ.get("GITHUB_PAGES_URL", "").rstrip("/")
    CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")
    TOP_N = int(os.environ.get("TOP_N", "15"))
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

    # RSS 源
    custom_feeds = os.environ.get("RSS_FEEDS", "").strip()
    if custom_feeds:
        RSS_FEEDS = [("自定义", url.strip()) for url in custom_feeds.split(",") if url.strip()]
    else:
        RSS_FEEDS = DEFAULT_RSS_FEEDS.copy()

    # 确保输出目录存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    _loaded = True
    logger.info("配置加载完成，共 %d 个 RSS 源", len(RSS_FEEDS))


def get_feeds() -> list[tuple[str, str]]:
    """获取 RSS 源列表。如果未调用 load()，返回默认列表。"""
    return RSS_FEEDS if RSS_FEEDS else DEFAULT_RSS_FEEDS


def get_anthropic_client_kwargs() -> dict:
    """构建 anthropic.Anthropic() 的参数字典，支持 base_url 和 auth_token。

    显式传入非空值，空值传 None 覆盖 SDK 从环境变量读到的空字符串。
    """
    kwargs: dict = {
        "api_key": ANTHROPIC_API_KEY or None,
        "auth_token": ANTHROPIC_AUTH_TOKEN or None,
    }
    if ANTHROPIC_BASE_URL:
        kwargs["base_url"] = ANTHROPIC_BASE_URL
    return kwargs
