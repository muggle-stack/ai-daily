"""筛选评分 prompt。"""

FILTER_SYSTEM_PROMPT = """你是一位资深 AI 行业分析师。请对以下文章列表进行评估和筛选。

评分标准：
- relevance (1-10): AI/ML/LLM 领域相关性。纯 AI 技术=10，泛科技=5，无关=1
- quality (1-10): 信息质量。重大发布/深度分析=10，新闻转述=5，营销软文=1
- timeliness (1-10): 时效价值。首次披露=10，跟进报道=6，旧闻=1

分类（选一个最匹配的）：
模型发布 | 开源项目 | 研究论文 | 产品动态 | 行业观点 | 工具技巧

请严格以 JSON 数组格式返回，不要包含其他文字，不要使用 markdown 代码块。每个元素：
{"url": "原文URL", "relevance": 分数, "quality": 分数, "timeliness": 分数, "category": "分类", "keywords": ["关键词1", "关键词2"]}"""


def build_filter_user_message(articles: list) -> str:
    """构建发送给 Claude 的用户消息，包含所有待评分文章。

    Args:
        articles: Article 对象列表。

    Returns:
        格式化的文章列表字符串。
    """
    parts = []
    for i, article in enumerate(articles, 1):
        summary = (article.summary or "")[:500]
        parts.append(
            f"[{i}] Title: {article.title}\n"
            f"URL: {article.url}\n"
            f"Source: {article.source}\n"
            f"Summary: {summary}"
        )
    return "\n\n".join(parts)
