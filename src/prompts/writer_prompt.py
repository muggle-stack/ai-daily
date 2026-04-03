"""摘要生成 prompt。"""

WRITER_SYSTEM_PROMPT = """你是一位资深科技编辑，擅长将 AI 领域的英文资讯翻译、提炼为高质量的中文日报。

写作要求：
1. 所有摘要必须是中文
2. 英文文章标题需翻译为中文，并在括号中保留英文原标题
3. 每篇文章的摘要 4-6 句话，重点突出"是什么"和"为什么重要"
4. 如果文章中有具体数据（参数量、性能指标、价格、用户数），必须保留
5. 语气：专业但不枯燥，像一位懂技术的编辑在和你聊天
6. 严格按照指定的 Markdown 格式输出

输出格式：

# AI Daily · {日期}

> {一句话综述：用 3 句话概括今天最重要的 3 件事}

---

## {分类emoji} {分类名称}

### {文章标题中文翻译}（{英文原标题}）
{4-6句结构化摘要}

🔗 [原文链接](url) · 来源：{source} · 关键词：#keyword1 #keyword2

---

（重复以上结构，按分类分组）

## 📊 今日关键词
#关键词1 #关键词2 #关键词3 ...

分类及对应 emoji：
- 🚀 模型发布
- 🔧 开源项目
- 📄 研究论文
- 📱 产品动态
- 💡 行业观点
- 🛠️ 工具技巧"""


def build_writer_user_message(articles_by_category: dict, date_str: str) -> str:
    """构建发送给 Claude 的用户消息。

    Args:
        articles_by_category: 按分类分组的文章字典，key 为分类名，value 为 ScoredArticle 列表。
        date_str: 日期字符串，如 "2026年04月02日"。

    Returns:
        格式化的文章列表字符串。
    """
    parts = [f"日期：{date_str}\n\n以下是今日筛选出的文章，请按分类生成日报：\n"]

    for category, articles in articles_by_category.items():
        parts.append(f"\n### 分类：{category}\n")
        for article in articles:
            keywords = ", ".join(article.keywords) if hasattr(article, "keywords") else ""
            parts.append(
                f"- 标题: {article.title}\n"
                f"  URL: {article.url}\n"
                f"  来源: {article.source}\n"
                f"  摘要: {(article.summary or '')[:800]}\n"
                f"  关键词: {keywords}\n"
                f"  综合评分: {article.composite_score:.1f}\n"
            )

    return "\n".join(parts)
