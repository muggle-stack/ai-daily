"""统一配置管理，所有 API key 从环境变量读取。"""

import os
from pathlib import Path
from urllib.parse import urlparse

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

# ===== 三层筛选配置 =====

# 源权重 — Layer 2 语义去重时优先保留高权重源
SOURCE_WEIGHTS: dict[str, int] = {
    "Anthropic Blog": 10,
    "OpenAI Blog": 10,
    "Google AI Blog": 10,
    "HuggingFace": 9,
    "机器之心": 8,
    "Simon Willison": 8,
    "Papers With Code": 8,
    "arXiv AI": 8,
    "Alignment Forum": 8,
    "SemiAnalysis": 8,
    "smol.ai": 7,
    "Hacker News": 7,
    "TechCrunch": 7,
    "VentureBeat": 7,
    "LangChain Blog": 7,
    "LlamaIndex Blog": 7,
    "量子位": 7,
    "The Chip Letter": 7,
    "Reddit ML": 6,
    "AI 前线": 6,
    "AI Safety Newsletter": 7,
    "36氪": 5,
}
DEFAULT_SOURCE_WEIGHT: int = 5

# Layer 1 黑名单关键词 — 标题或摘要命中则直接过滤
BLACKLIST_KEYWORDS: list[str] = [
    "sponsor", "newsletter", "月报", "赞助", "sponsors-only",
    "周报", "招聘", "hiring", "job posting", "unsubscribe",
    "广告", "promoted",
]

# Layer 1 最小内容长度（title + summary 合计字符数）
MIN_CONTENT_LENGTH: int = 30

# Layer 2 语义去重相似度阈值
DEDUP_SIMILARITY_THRESHOLD: float = 0.6

# Layer 3 四维评分权重
SCORE_WEIGHTS: dict[str, float] = {
    "relevance": 0.30,
    "novelty": 0.30,
    "depth": 0.20,
    "source_credibility": 0.20,
}

# 个人兴趣关键词 — 匹配到的文章额外加分
PERSONAL_INTERESTS: list[str] = [
    "RISC-V", "edge inference", "边缘推理",
    "quantization", "量化", "INT4", "INT8",
    "inference engine", "推理引擎",
    "on-device", "端侧",
    "TTS", "ASR", "语音",
    "agent", "workflow", "工作流",
]
PERSONAL_INTEREST_BOOST: float = 2.0

# URL 域名 → 源名称映射（用于自定义 RSS 源名称推导）
DOMAIN_NAME_MAP: dict[str, str] = {
    "hnrss.org": "Hacker News",
    "huggingface.co": "HuggingFace",
    "simonwillison.net": "Simon Willison",
    "reddit.com": "Reddit ML",
    "blog.google": "Google AI Blog",
    "openai.com": "OpenAI Blog",
    "anthropic.com": "Anthropic Blog",
    "news.smol.ai": "smol.ai",
    "jiqizhixin.com": "机器之心",
    "36kr.com": "36氪",
    "rsshub.app/36kr": "36氪",
    "rsshub.app/jiqizhixin": "机器之心",
    "semianalysis.com": "SemiAnalysis",
    "thechipletter.substack.com": "The Chip Letter",
    "alignmentforum.org": "Alignment Forum",
    "newsletter.safe.ai": "AI Safety Newsletter",
    "paperswithcode.com": "Papers With Code",
    "arxiv.org": "arXiv AI",
    "techcrunch.com": "TechCrunch",
    "venturebeat.com": "VentureBeat",
    "qbitai.com": "量子位",
    "infoq.cn": "AI 前线",
    "blog.langchain.dev": "LangChain Blog",
    "llamaindex.ai": "LlamaIndex Blog",
}

# 板块映射 — 6 个细分类归入 4 个板块（用于首页概览展示）
SECTION_MAP: dict[str, str] = {
    "开源项目": "开发生态",
    "工具技巧": "开发生态",
    "模型发布": "产品应用",
    "产品动态": "产品应用",
    "行业观点": "行业动态",
    "研究论文": "研究前沿",
}

SECTION_ICONS: dict[str, str] = {
    "开发生态": "code",
    "产品应用": "devices",
    "行业动态": "trending_up",
    "研究前沿": "science",
}

SECTION_ORDER: list[str] = ["产品应用", "开发生态", "行业动态", "研究前沿"]

# ===== 默认 RSS 源 =====
DEFAULT_RSS_FEEDS: list[tuple[str, str]] = [
    # 综合 AI 新闻
    ("smol.ai", "https://news.smol.ai/rss"),
    ("Hacker News", "https://hnrss.org/newest?q=AI+LLM+GPT+Claude&count=30"),
    ("Reddit ML", "https://www.reddit.com/r/MachineLearning/.rss"),
    # 官方博客
    ("Google AI Blog", "https://blog.google/technology/ai/rss/"),
    ("OpenAI Blog", "https://openai.com/blog/rss.xml"),
    ("Anthropic Blog", "https://www.anthropic.com/rss.xml"),
    ("HuggingFace Blog", "https://huggingface.co/blog/feed.xml"),
    # 个人/技术博客
    ("Simon Willison", "https://simonwillison.net/atom/everything/"),
    # AI 硬件
    ("SemiAnalysis", "https://www.semianalysis.com/feed"),
    ("The Chip Letter", "https://thechipletter.substack.com/feed"),
    # AI 安全
    ("Alignment Forum", "https://www.alignmentforum.org/feed.xml"),
    # 学术论文
    ("Papers With Code", "https://paperswithcode.com/latest/rss"),
    ("arXiv AI", "https://rss.arxiv.org/rss/cs.AI"),
    # 行业媒体
    ("TechCrunch", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("VentureBeat", "https://venturebeat.com/category/ai/feed/"),
    # Agent/工具
    ("LangChain Blog", "https://blog.langchain.dev/rss/"),
    ("LlamaIndex Blog", "https://www.llamaindex.ai/blog/rss"),
    # 中文源
    ("机器之心", "https://www.jiqizhixin.com/rss"),
    ("量子位", "https://www.qbitai.com/feed"),
    ("36氪", "https://www.36kr.com/feed"),
]

RSS_FEEDS: list[tuple[str, str]] = []

_loaded = False


def _derive_source_name(url: str) -> str:
    """从 URL 推导源名称，优先查 DOMAIN_NAME_MAP，否则用域名。"""
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        path = parsed.path or ""
    except Exception:
        return "Unknown"
    # 精确匹配域名
    if host in DOMAIN_NAME_MAP:
        return DOMAIN_NAME_MAP[host]
    # 去 www. 后再试
    bare = host.removeprefix("www.")
    if bare in DOMAIN_NAME_MAP:
        return DOMAIN_NAME_MAP[bare]
    # 域名+路径匹配（如 rsshub.app/36kr → 36氪）
    full = bare + path
    for key, name in DOMAIN_NAME_MAP.items():
        if key in full:
            return name
    return bare or "Unknown"


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
        RSS_FEEDS = []
        for url in custom_feeds.split(","):
            url = url.strip()
            if not url:
                continue
            name = _derive_source_name(url)
            RSS_FEEDS.append((name, url))
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
