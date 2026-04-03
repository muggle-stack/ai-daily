# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Automated AI news daily report system (AI Daily). Fetches AI-related articles from RSS feeds, uses Claude API to filter/score/summarize, renders HTML output, uploads to Feishu (Lark) Drive folder and creates online docx with group notifications. Runs daily via GitHub Actions at UTC 00:00 (Beijing 08:00).

The full engineering spec is in `ai_daily.md` — refer to it for detailed requirements.

## Tech Stack

- Python 3.11+
- feedparser (RSS parsing), requests (HTTP), anthropic (Claude API), python-dotenv (.env loading)
- No other external dependencies — intentionally minimal

## Architecture

Five sequential agents orchestrated by `src/main.py`:

1. **RSS Agent** (`src/agents/rss_agent.py`) — Concurrent RSS fetching (10 threads, 15s timeout), 24-48h window filter, URL dedup
2. **Filter Agent** (`src/agents/filter_agent.py`) — Claude API batch scoring on 3 dimensions (relevance×0.4 + quality×0.35 + timeliness×0.25), top-N selection + categorization into 6 categories (模型发布/开源项目/研究论文/产品动态/行业观点/工具技巧)
3. **Writer Agent** (`src/agents/writer_agent.py`) — Claude API Chinese summary generation, structured Markdown output grouped by category
4. **Renderer Agent** (`src/agents/renderer_agent.py`) — Python template-based HTML rendering (no LLM), warm card-style theme, single-file HTML with inline CSS
5. **Feishu Agent** (`src/agents/feishu_agent.py`) — Feishu tenant token auth (2h cache), Drive API upload, Docx API online document creation with Markdown-to-block conversion (max 50 blocks/batch), optional group card notification

Data flow with types: `Article` → `ScoredArticle` → Markdown `str` → HTML `str` + Feishu docx

### Prompt Templates

Claude API prompts live in `src/prompts/`, separate from agent logic:
- `filter_prompt.py` — Scoring criteria and article formatting for filter agent
- `writer_prompt.py` — Role definition, output format, emoji mappings for writer agent
- `renderer_prompt.py` — HTML/CSS templates and category color maps for renderer (no LLM, just templates)

To change Claude's scoring/writing behavior, edit prompt files. To change pipeline logic, edit agent files.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Full pipeline
python src/main.py

# With custom params
python src/main.py --hours 48 --top-n 20

# Test individual agents (each has __main__ block)
python -m src.agents.rss_agent
python -m src.agents.filter_agent
python -m src.agents.renderer_agent
```

## Configuration

All secrets/config via environment variables (see `.env.example`). Required: `ANTHROPIC_API_KEY`, `FEISHU_APP_ID`, `FEISHU_APP_SECRET`, `FEISHU_FOLDER_TOKEN`. Config is centralized in `src/config.py`.

## Key Design Decisions

- Each agent is independently testable via `python -m`
- Claude API calls use batch mode (send all articles in one request, get JSON array back)
- HTML renderer uses Python string templates, NOT Claude — for speed and consistency
- Feishu publish: Drive API uploads HTML file to folder, Docx API creates online document with Markdown→block conversion; fallback to simple text if conversion fails
- Error isolation: each agent catches its own exceptions; one failing RSS source or API call doesn't kill the pipeline
- Claude API and Feishu API retries: 2 retries with 5s interval (`_call_claude_with_retry` pattern shared across filter/writer agents)
- Zero articles after filtering → log and exit cleanly, no empty report pushed
- GitHub Actions deploys `output/` to GitHub Pages incrementally (keeps existing daily files)

## Code Conventions

- Type hints on all functions
- Docstrings on all functions
- No `print()` — use `logging` exclusively (via `src/utils/logger.py`)
- No hardcoded config — everything through `src/config.py`
- Output files go to `output/` directory (gitignored)
- All output (summaries, titles) in Chinese; preserve original English titles alongside translations

## Other

- `juya-news-card/` — Separate Next.js sub-project for card rendering UI (independent from the Python pipeline)
