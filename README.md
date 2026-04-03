# AI Daily — AI 资讯日报自动化系统

每天自动从多个 RSS 源抓取 AI 领域资讯，通过 Claude AI 智能筛选、评分、生成中文摘要，以精美 HTML 文档上传到飞书云空间文件夹，同时创建飞书在线文档，并发送飞书群通知。

## 效果预览

<!-- TODO: 添加效果截图 -->

## 快速开始

### 1. 克隆项目

```bash
git clone <repo-url>
cd ai-daily
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 API Key
```

### 3. 安装依赖并运行

```bash
pip install -r requirements.txt
python src/main.py
```

## 飞书应用配置

### 创建飞书自建应用

1. 访问 [飞书开放平台](https://open.feishu.cn/app)，创建企业自建应用
2. 获取 App ID 和 App Secret
3. 在「权限管理」中申请以下权限：

```
drive:drive                # 云空间 - 查看、创建、编辑、上传文件
drive:drive:readonly       # 云空间 - 查看文件
docx:document              # 文档 - 查看、创建、编辑文档
docx:document:readonly     # 文档 - 查看文档
im:message:send_as_bot     # 消息 - 以应用身份发送消息
```

4. 发布应用并审批通过

### 获取文件夹配置

1. 打开飞书云空间，找到目标文件夹
2. 从 URL 中获取 `folder_token`（URL 格式：`https://xxx.feishu.cn/drive/folder/{folder_token}`）
3. 将 `folder_token` 填入 `.env` 文件的 `FEISHU_FOLDER_TOKEN`

### 配置群通知（可选）

1. 将应用机器人添加到目标群
2. 获取群的 `chat_id`（可通过飞书 API 调试台获取）
3. 填入 `.env` 文件的 `FEISHU_CHAT_ID`

## GitHub Actions 配置

1. 在 GitHub 仓库 Settings → Secrets and variables → Actions 中添加以下 Secrets：
   - `ANTHROPIC_API_KEY`
   - `FEISHU_APP_ID`
   - `FEISHU_APP_SECRET`
   - `FEISHU_FOLDER_TOKEN`
   - `FEISHU_CHAT_ID`（可选）

2. 系统会在每天北京时间 8:00 自动运行，也可在 Actions 页面手动触发

## 自定义 RSS 源

在 `.env` 中设置 `RSS_FEEDS` 变量，多个源用逗号分隔：

```bash
RSS_FEEDS=https://example.com/rss1.xml,https://example.com/rss2.xml
```

不设置则使用内置的 10 个默认源（含中英文）。

## 项目结构

```
ai-daily/
├── src/
│   ├── main.py                 # 主入口，编排所有 Agent
│   ├── config.py               # 统一配置管理
│   ├── agents/
│   │   ├── rss_agent.py        # RSS 抓取 + 去重
│   │   ├── filter_agent.py     # AI 智能筛选 + 评分
│   │   ├── writer_agent.py     # AI 摘要生成 + 分类编排
│   │   ├── renderer_agent.py   # HTML 渲染
│   │   └── feishu_agent.py     # 飞书 Drive 上传 + 在线文档 + 群通知
│   ├── prompts/                # Prompt 模板
│   └── utils/                  # 工具函数
├── output/                     # 生成的日报文件
├── .github/workflows/daily.yml # GitHub Actions 定时任务
├── requirements.txt
└── .env.example
```

## 调试命令

```bash
# 只跑 RSS 抓取
python -m src.agents.rss_agent

# 只跑 AI 筛选（需要 ANTHROPIC_API_KEY）
python -m src.agents.filter_agent

# 只跑渲染（读取上次的 Markdown）
python -m src.agents.renderer_agent

# 完整流程
python src/main.py

# 指定参数
python src/main.py --hours 48 --top-n 20
```

## FAQ

**Q: 运行后没有抓取到文章？**
A: 部分 RSS 源可能有地区访问限制或临时不可用。系统会跳过失败的源继续运行。可以通过 `LOG_LEVEL=DEBUG` 查看详细日志。

**Q: 飞书推送失败？**
A: 请检查：1) 应用权限是否已审批（需要 drive 和 docx 权限）；2) 应用是否有目标文件夹的访问权限；3) `FEISHU_FOLDER_TOKEN` 是否正确。

**Q: 如何修改日报的样式？**
A: HTML 模板在 `src/prompts/renderer_prompt.py` 中定义，可以直接修改 CSS 样式。

**Q: Claude API 调用费用大约多少？**
A: 每次运行调用 2 次 Claude API（筛选 + 摘要），使用 claude-sonnet-4-20250514 模型，每次约 $0.01-0.05，取决于文章数量。
