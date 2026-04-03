# AI 日报 — 每天更新最新行业动态

每天自动从 20+ 个 RSS 源抓取 AI 领域资讯，通过三层筛选架构（规则过滤 → 语义去重 → 多板块 AI 评分）精选 TOP 文章，生成中文摘要，渲染为站点化 HTML 页面，同时推送到飞书和 GitHub Pages。

## 效果预览

<!-- TODO: 添加效果截图 -->

## 快速开始

### 1. 克隆项目

```bash
git clone <repo-url>
cd daily-report
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入 API Key
```

### 3. 安装依赖并运行

```bash
pip install -r requirements.txt
python -m src.main
```

生成结果在 `output/` 目录，浏览器打开 `output/index.html` 查看。

## 架构

### 三层筛选 Pipeline

```
RSS 抓取（20+ 源，单源上限 30 篇）
  → Layer 1: 规则过滤（黑名单、最小长度、AI 相关性关键词）
  → Layer 2: 语义去重（标题相似度 + 关键词重叠检测）
  → Layer 3: 4 板块 Agent 串行评分（产品应用/开发生态/行业动态/研究前沿）
  → 个性化兴趣加分 → TOP N 排序
```

### Agent 编排

| Agent | 职责 |
|-------|------|
| RSS Agent | 并发抓取 20+ RSS 源，URL 去重 |
| Prefilter | 规则过滤 + 语义去重 + 个性化加分 |
| Filter Agent | 4 个板块 Agent 四维评分（relevance/novelty/depth/source_credibility） |
| Writer Agent | Claude 生成中文摘要，按分类编排 Markdown |
| Renderer Agent | Tailwind 双列网格 HTML 渲染，站点化输出 |
| Site Builder | 首页生成 + reports.js 索引维护 |
| Feishu Agent | 飞书在线文档 + 群卡片通知 |

### 站点化输出

```
output/
├── index.html          ← 首页（最新一期概览 + 往期归档）
├── reports.js          ← 报告元数据索引
└── reports/
    ├── 2026-04-03.html ← 每日报告页（双列网格布局）
    └── 2026-04-03.md   ← Markdown 归档
```

## 配置

所有配置通过环境变量管理（见 `.env.example`）。

**必填**：`ANTHROPIC_API_KEY`（或 `ANTHROPIC_AUTH_TOKEN`）、`FEISHU_APP_ID`、`FEISHU_APP_SECRET`

**可选**：`FEISHU_FOLDER_TOKEN`、`FEISHU_CHAT_ID`、`GITHUB_PAGES_URL`、`CLAUDE_MODEL`、`TOP_N`、`RSS_FEEDS`

自定义 RSS 源在 `.env` 中设置 `RSS_FEEDS`（逗号分隔 URL），不设置则使用内置 20 个默认源。源名称从 URL 自动推导。

## 飞书应用配置

1. 访问 [飞书开放平台](https://open.feishu.cn/app)，创建企业自建应用
2. 申请权限：`drive:drive`、`docx:document`、`im:message:send_as_bot`
3. 发布并审批，获取 App ID / App Secret
4. 从飞书云空间 URL 获取 `folder_token`，群设置获取 `chat_id`

## 调试命令

```bash
# 单独测试各 Agent
python -m src.agents.rss_agent         # RSS 抓取
python -m src.agents.prefilter         # 预过滤（规则 + 去重）
python -m src.agents.filter_agent      # AI 评分
python -m src.agents.renderer_agent    # HTML 渲染

# 完整流程
python -m src.main
python -m src.main --hours 48 --top-n 20

# HTTP 服务（供 OpenClaw 调用）
python -m src.server
```

## GitHub Pages 部署

项目使用 gh-pages 分支部署静态站点，每天 pipeline 运行后将 `output/` 内容推送到该分支。也可通过 GitHub Actions 自动部署。

## FAQ

**Q: 运行后没有抓取到文章？**
A: 部分 RSS 源可能有地区访问限制。系统会跳过失败的源继续运行。`LOG_LEVEL=DEBUG` 查看详细日志。

**Q: 评分时报 429 限流？**
A: 4 个板块 Agent 已改为串行执行（每次间隔 3s），如仍触发限流可在 `.env` 中减少 `TOP_N` 或减少 RSS 源。

**Q: 飞书推送失败？**
A: 检查：1) 应用权限已审批；2) 应用有目标文件夹访问权限；3) `FEISHU_FOLDER_TOKEN` 正确。

**Q: 如何修改日报样式？**
A: HTML 模板在 `src/prompts/renderer_prompt.py`，使用 Tailwind CSS。首页模板为 `INDEX_PAGE_TEMPLATE`，报告页模板为 `HTML_TEMPLATE`。
