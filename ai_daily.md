# AI 每日早报自动化工作流 — 完整工程规格

## 项目概述

构建一个完全自动化的 AI 资讯日报系统。每天定时从多个 RSS 源抓取 AI 领域资讯，通过 LLM 智能筛选、评分、分类、生成中文摘要，最终以精美 HTML 文档形式推送到飞书知识库，并发送飞书群通知。

整个系统通过 GitHub Actions 每天北京时间 8:00 自动运行，无需人工干预。

## 技术栈

- Python 3.11+
- feedparser（RSS 解析）
- requests（HTTP 请求）
- Anthropic Python SDK（Claude API 调用）
- 无其他外部依赖，保持极简

## 项目结构

```
ai-daily/
├── src/
│   ├── main.py                 # 主入口，编排所有 Agent
│   ├── config.py               # 统一配置管理，所有 API key 从环境变量读取
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── rss_agent.py        # Agent 1: RSS 抓取 + 去重
│   │   ├── filter_agent.py     # Agent 2: AI 智能筛选 + 评分
│   │   ├── writer_agent.py     # Agent 3: AI 摘要生成 + 分类编排
│   │   ├── renderer_agent.py   # Agent 4: HTML 渲染（Claude 风格深色主题）
│   │   └── feishu_agent.py     # Agent 5: 飞书知识库写入 + 群通知
│   ├── prompts/
│   │   ├── filter_prompt.py    # 筛选评分 prompt
│   │   ├── writer_prompt.py    # 摘要生成 prompt
│   │   └── renderer_prompt.py  # HTML 渲染 prompt（含主题模板）
│   └── utils/
│       ├── __init__.py
│       └── logger.py           # 统一日志
├── output/                     # 本地输出目录（.gitignore）
├── .env.example                # 环境变量模板
├── .github/
│   └── workflows/
│       └── daily.yml           # GitHub Actions 定时任务
├── requirements.txt
└── README.md
```

## 配置管理（config.py）

所有密钥和配置从环境变量读取，用户只需要填 `.env` 文件：

```python
# 必填
ANTHROPIC_API_KEY      # Claude API Key
FEISHU_APP_ID          # 飞书自建应用 App ID
FEISHU_APP_SECRET      # 飞书自建应用 App Secret
FEISHU_WIKI_SPACE_ID   # 飞书知识库空间 ID
FEISHU_WIKI_PARENT_TOKEN  # 知识库父节点 token（日报写入这个节点下）

# 选填
FEISHU_CHAT_ID         # 飞书群 chat_id（发送群通知，不填则不发通知）
CLAUDE_MODEL           # 默认 claude-sonnet-4-20250514
RSS_FEEDS              # 自定义 RSS 源，逗号分隔（有默认值）
TOP_N                  # 最终保留的文章数量，默认 15
LOG_LEVEL              # 默认 INFO
```

## Agent 1: RSS 抓取（rss_agent.py）

职责：并发抓取多个 RSS 源，提取文章元数据，按时间窗口过滤，去重。

默认 RSS 源列表（硬编码，可通过环境变量覆盖）：
```
# 英文源
https://news.smol.ai/rss          # smol.ai AI 日报
https://hnrss.org/newest?q=AI+LLM+GPT+Claude&count=30  # Hacker News AI 相关
https://www.reddit.com/r/MachineLearning/.rss            # Reddit ML
https://blog.google/technology/ai/rss/                   # Google AI Blog
https://openai.com/blog/rss.xml                          # OpenAI Blog
https://www.anthropic.com/rss.xml                        # Anthropic Blog
https://huggingface.co/blog/feed.xml                     # HuggingFace Blog
https://simonwillison.net/atom/everything/               # Simon Willison

# 中文源
https://www.jiqizhixin.com/rss                           # 机器之心
https://www.36kr.com/feed                                # 36氪（需过滤 AI 相关）
```

输出数据结构：
```python
@dataclass
class Article:
    title: str
    url: str
    source: str        # RSS 源名称
    published: datetime
    summary: str       # RSS 自带的摘要/description
    content: str       # 全文内容（如果有）
```

实现要点：
- 使用 feedparser 解析
- 10 路并发（concurrent.futures.ThreadPoolExecutor）
- 每个源 15 秒超时
- 只保留过去 24-48 小时内的文章
- 按 URL 去重
- 输出时按发布时间倒序排列
- 每个源抓取失败不影响其他源，记录 warning 日志

## Agent 2: AI 智能筛选（filter_agent.py）

职责：调用 Claude API，对每篇文章从三个维度打分（1-10），过滤低质量内容。

评分维度：
1. **相关性**（AI/ML/LLM 领域相关度）
2. **质量**（信息密度、原创性、不是水文或营销）
3. **时效性**（是否是新进展、新发布，而不是旧闻重炒）

实现方式：
- 将所有文章的 title + summary 拼成一个 batch，一次性发给 Claude
- Prompt 要求 Claude 返回 JSON 数组：`[{"url": "...", "relevance": 8, "quality": 7, "timeliness": 9, "category": "模型发布", "keywords": ["Claude", "Anthropic"]}]`
- 综合分 = relevance * 0.4 + quality * 0.35 + timeliness * 0.25
- 取 TOP_N（默认 15）篇
- 同时完成分类，预定义类别：模型发布、开源项目、研究论文、产品动态、行业观点、工具技巧

Prompt 设计（filter_prompt.py）：
```
你是一位资深 AI 行业分析师。请对以下文章列表进行评估和筛选。

评分标准：
- relevance (1-10): AI/ML/LLM 领域相关性。纯 AI 技术=10，泛科技=5，无关=1
- quality (1-10): 信息质量。重大发布/深度分析=10，新闻转述=5，营销软文=1  
- timeliness (1-10): 时效价值。首次披露=10，跟进报道=6，旧闻=1

分类（选一个最匹配的）：
模型发布 | 开源项目 | 研究论文 | 产品动态 | 行业观点 | 工具技巧

请严格以 JSON 数组格式返回，不要包含其他文字。每个元素：
{"url": "原文URL", "relevance": 分数, "quality": 分数, "timeliness": 分数, "category": "分类", "keywords": ["关键词1", "关键词2"]}
```

## Agent 3: 摘要生成（writer_agent.py）

职责：为筛选后的 TOP N 文章生成结构化中文摘要，编排成完整日报文档。

实现方式：
- 将筛选后的文章按类别分组
- 一次性发给 Claude，要求生成结构化 Markdown
- 包含：日期标题、一句话综述（3句话概括今天最重要的事）、按分类展示的文章摘要

输出 Markdown 格式：
```markdown
# AI Daily · {YYYY年MM月DD日}

> {一句话综述：今天 AI 圈最重要的 3 件事}

---

## 🚀 模型发布

### {文章标题中文翻译}
{4-6句结构化摘要，包含：是什么、为什么重要、关键数据/指标}

🔗 [原文链接](url) · 来源：{source} · 关键词：#tag1 #tag2

---

## 🔧 开源项目
...

## 📊 今日关键词
#Anthropic #Claude #GPT #开源 ...
```

Prompt 设计要点：
- 摘要必须是中文
- 英文标题需要翻译但保留原文
- 每篇摘要 4-6 句，重点突出"是什么"和"为什么重要"
- 如果有具体数据（参数量、性能指标、价格），必须保留
- 语气：专业但不枯燥，像一位懂技术的编辑在和你聊天

## Agent 4: HTML 渲染（renderer_agent.py）

职责：将 Markdown 日报渲染为精美的单文件 HTML 页面。

**不使用 Claude 生成 HTML**，而是用 Python 模板引擎直接渲染（更快、更稳定、更一致）。

HTML 模板设计（Claude 深色科技风格）：

```
视觉规格：
- 背景：#0a0a0a 纯黑，顶部有微妙的蓝紫色径向渐变光晕
- 主色：#7c5cfc（紫色），辅助色：#00d4ff（青色）
- 文字：标题 #ffffff，正文 #e0e0e0，辅助信息 #888888
- 字体：system-ui, -apple-system, sans-serif
- 卡片：背景 #141414，边框 1px solid #222，圆角 12px，hover 时边框变为主色
- 分类标签：带主色背景的小 pill，半透明
- 链接：青色 #00d4ff，hover 时亮度增加
- 最大宽度 720px，居中，响应式
- 顶部大标题 "AI Daily" 带渐变色（紫→青）
- 日期和统计信息（共 N 篇，来自 M 个源）
- 底部 footer 带生成时间戳
- 单文件 HTML，所有 CSS 内联，无外部依赖
- 中文友好的行高 1.8，段落间距
```

实现方式：
- 用 Python string.Template 或简单的 f-string 渲染
- 将 Markdown 中的结构化内容解析后填入 HTML 模板
- 同时保存 Markdown 和 HTML 到 output/ 目录
- HTML 文件命名：`ai-daily-{YYYY-MM-DD}.html`

## Agent 5: 飞书推送（feishu_agent.py）

职责：将生成的日报写入飞书知识库文档，并发送群聊通知。

### 5.1 获取 tenant_access_token

```
POST https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/
Body: {"app_id": "...", "app_secret": "..."}
```
Token 缓存 2 小时（飞书 token 有效期 2h）。

### 5.2 在知识库创建文档节点

```
POST https://open.feishu.cn/open-apis/wiki/v2/spaces/{space_id}/nodes
Headers: Authorization: Bearer {tenant_access_token}
Body: {
  "obj_type": "doc",
  "parent_node_token": "{parent_token}",
  "node_type": "origin",
  "title": "AI Daily · {YYYY-MM-DD}"
}
```

### 5.3 写入文档内容

使用飞书文档 API 写入富文本内容。将 Markdown 转换为飞书文档的 block 结构：

```
POST https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/blocks/{block_id}/children
```

飞书文档 block 类型映射：
- `# 标题` → heading1 block
- `## 标题` → heading2 block  
- `### 标题` → heading3 block
- 正文段落 → text block（支持加粗、链接等 inline 样式）
- `> 引用` → quote block
- `---` → divider block
- 关键词标签 → text block with colored inline code

实现要点：
- 先创建空文档获取 document_id
- 然后批量写入 blocks（飞书支持 batch create）
- Markdown 到飞书 block 的转换需要一个 `md_to_feishu_blocks()` 工具函数
- 保留链接（text_run with link）
- 如果 Markdown → 飞书 block 转换过于复杂，降级方案：直接将 HTML 内容作为附件上传，在文档中嵌入链接

### 5.4 发送群通知（可选）

如果配置了 FEISHU_CHAT_ID，发送一条卡片消息到群：

```
POST https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id
Body: {
  "receive_id": "{chat_id}",
  "msg_type": "interactive",
  "content": "{飞书卡片 JSON}"
}
```

卡片内容：
```json
{
  "config": {"wide_screen_mode": true},
  "header": {
    "title": {"tag": "plain_text", "content": "🤖 AI Daily · {日期}"},
    "template": "purple"
  },
  "elements": [
    {"tag": "markdown", "content": "{一句话综述}"},
    {"tag": "markdown", "content": "📰 共 {N} 篇精选，涵盖 {分类列表}"},
    {"tag": "action", "actions": [
      {"tag": "button", "text": {"tag": "plain_text", "content": "📖 查看完整日报"}, "url": "{知识库文档链接}", "type": "primary"}
    ]}
  ]
}
```

## 主入口编排（main.py）

```python
"""
AI Daily 主入口
编排所有 Agent 按顺序执行，每个 Agent 独立负责自己的模块。
"""

def main():
    # 1. RSS Agent: 抓取原始文章
    raw_articles = rss_agent.fetch_all()
    log(f"抓取到 {len(raw_articles)} 篇文章")

    # 2. Filter Agent: AI 筛选评分
    scored_articles = filter_agent.filter_and_score(raw_articles)
    top_articles = scored_articles[:config.TOP_N]
    log(f"筛选出 TOP {len(top_articles)} 篇")

    # 3. Writer Agent: 生成结构化摘要
    markdown_report = writer_agent.generate_report(top_articles)
    save_to_file(markdown_report, f"output/ai-daily-{today}.md")

    # 4. Renderer Agent: 渲染 HTML
    html_report = renderer_agent.render_html(markdown_report, top_articles)
    save_to_file(html_report, f"output/ai-daily-{today}.html")

    # 5. Feishu Agent: 推送到飞书
    doc_url = feishu_agent.create_wiki_doc(markdown_report)
    if config.FEISHU_CHAT_ID:
        feishu_agent.send_group_notification(doc_url, top_articles)

    log(f"完成！文档链接：{doc_url}")
```

## GitHub Actions 定时任务（.github/workflows/daily.yml）

```yaml
name: AI Daily Report

on:
  schedule:
    - cron: '0 0 * * *'    # UTC 0:00 = 北京时间 8:00
  workflow_dispatch:         # 支持手动触发

jobs:
  generate-daily:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run AI Daily
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          FEISHU_APP_ID: ${{ secrets.FEISHU_APP_ID }}
          FEISHU_APP_SECRET: ${{ secrets.FEISHU_APP_SECRET }}
          FEISHU_WIKI_SPACE_ID: ${{ secrets.FEISHU_WIKI_SPACE_ID }}
          FEISHU_WIKI_PARENT_TOKEN: ${{ secrets.FEISHU_WIKI_PARENT_TOKEN }}
          FEISHU_CHAT_ID: ${{ secrets.FEISHU_CHAT_ID }}
        run: python src/main.py

      - name: Upload artifacts
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: daily-report-${{ github.run_id }}
          path: output/
          retention-days: 30
```

## .env.example

```bash
# ===== 必填 =====
ANTHROPIC_API_KEY=sk-ant-xxxxx
FEISHU_APP_ID=cli_xxxxx
FEISHU_APP_SECRET=xxxxx
FEISHU_WIKI_SPACE_ID=xxxxx
FEISHU_WIKI_PARENT_TOKEN=xxxxx

# ===== 选填 =====
FEISHU_CHAT_ID=oc_xxxxx
CLAUDE_MODEL=claude-sonnet-4-20250514
TOP_N=15
LOG_LEVEL=INFO
```

## requirements.txt

```
feedparser>=6.0
requests>=2.31
anthropic>=0.40
```

## 错误处理要求

- 每个 Agent 内部捕获异常，不影响其他 Agent
- RSS 某个源挂了 → 跳过，继续其他源
- Claude API 调用失败 → 重试 2 次，间隔 5 秒
- 飞书 API 调用失败 → 重试 2 次，记录错误日志
- 如果筛选后文章数为 0 → 记录日志，正常退出，不推送空报告
- 所有日志带时间戳，输出到 stdout（GitHub Actions 自动捕获）

## 代码规范

- 类型注解（type hints）全覆盖
- 每个函数都有 docstring
- 配置不硬编码，全部走 config.py
- 无 print，全部用 logging
- 每个 Agent 可以独立测试运行

## 测试命令

实现以下测试命令用于调试：

```bash
# 只跑 RSS 抓取
python -m src.agents.rss_agent

# 只跑 AI 筛选（读取上次抓取的缓存）
python -m src.agents.filter_agent

# 只跑渲染（读取上次的 Markdown）
python -m src.agents.renderer_agent

# 完整流程
python src/main.py

# 指定日期范围
python src/main.py --hours 48 --top-n 20
```

## 飞书应用权限清单

告诉用户在飞书开放平台创建应用时需要开通的权限：

```
wiki:wiki                  # 知识库 - 查看、创建、编辑知识库
wiki:wiki:readonly         # 知识库 - 查看知识库
docx:document              # 文档 - 查看、创建、编辑文档
docx:document:readonly     # 文档 - 查看文档
im:message:send_as_bot     # 消息 - 以应用身份发送消息
```

## README.md 内容要求

README 需要包含：
1. 项目简介 + 效果截图占位符
2. 快速开始（3 步：clone → 配置 .env → 手动运行测试）
3. 飞书应用配置详细步骤（带截图说明文字）
4. GitHub Actions 配置步骤
5. 自定义 RSS 源说明
6. 项目结构说明
7. FAQ

---

**请按照以上规格完整实现所有文件。确保每个 Agent 模块独立、可测试、职责单一。用户 clone 仓库后，只需要填写 .env 文件的 API key，运行 `python src/main.py` 即可看到完整的日报生成和飞书推送效果。**
