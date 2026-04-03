# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Automated AI news daily report system (AI Daily). Fetches AI-related articles from RSS feeds, uses a 3-layer filtering pipeline (rule-based → semantic dedup → Claude AI scoring) to select top articles, generates Chinese summaries, renders HTML output, uploads to Feishu (Lark) Drive and sends group notifications. Also integrates with OpenClaw via FastAPI HTTP bridge. Runs daily via GitHub Actions or OpenClaw cron.

The full engineering spec is in `ai_daily.md` — refer to it for detailed requirements.

## Tech Stack

- Python 3.11+
- feedparser (RSS parsing), requests (HTTP), anthropic (Claude API), python-dotenv (.env loading)
- fastapi + uvicorn (HTTP bridge for OpenClaw integration)

## Architecture

Five sequential agents orchestrated by `src/main.py`, with a 3-layer filtering pipeline:

1. **RSS Agent** (`src/agents/rss_agent.py`) — Concurrent RSS fetching (10 threads, 15s timeout), 24-48h window filter, URL dedup
2. **Prefilter** (`src/agents/prefilter.py`) — Called by filter agent before Claude API:
   - **Layer 1 Rule Filter**: HTML tag stripping, blacklist keyword removal, minimum content length check
   - **Layer 2 Semantic Dedup**: `difflib.SequenceMatcher` title similarity (>0.6) + keyword overlap detection, keeps highest source-weight article
   - **Personal Boost**: +2 score for articles matching `PERSONAL_INTERESTS` keywords in config
3. **Filter Agent** (`src/agents/filter_agent.py`) — **Layer 3 AI Scoring**: Claude API 4-dimension scoring (relevance×0.30 + novelty×0.30 + depth×0.20 + source_credibility×0.20), `reject_reason` field for explicit rejection, personal interest boost added to composite score
4. **Writer Agent** (`src/agents/writer_agent.py`) — Claude API Chinese summary generation, structured Markdown output grouped by category
5. **Renderer Agent** (`src/agents/renderer_agent.py`) — Python template-based HTML rendering (no LLM), warm card-style theme with score badges, publish times, featured article styling, single-file HTML with inline CSS
6. **Feishu Agent** (`src/agents/feishu_agent.py`) — Feishu tenant token auth (2h cache), Drive API upload, Docx API online document creation with Markdown-to-block conversion (max 50 blocks/batch), optional group card notification

Data flow: `Article` → prefilter → `ScoredArticle` (4-dim + boost) → Markdown `str` → HTML `str` + Feishu docx

### 3-Layer Filtering Pipeline

```
RSS articles (30-100+)
  → Layer 1: Rule filter (blacklist, min length, HTML strip)
  → Layer 2: Semantic dedup (title similarity + keyword overlap)
  → Layer 3: Claude 4-dim scoring + reject_reason
  → Personal interest boost (+2)
  → TOP N by composite_score
```

Filtering config constants are centralized in `src/config.py`: `SOURCE_WEIGHTS`, `BLACKLIST_KEYWORDS`, `PERSONAL_INTERESTS`, `SCORE_WEIGHTS`, `DEDUP_SIMILARITY_THRESHOLD`.

### Prompt Templates

Claude API prompts live in `src/prompts/`, separate from agent logic:
- `filter_prompt.py` — 4-dimension scoring criteria (relevance/novelty/depth/source_credibility) with explicit high/mid/low score definitions
- `writer_prompt.py` — Role definition, output format, emoji mappings for writer agent
- `renderer_prompt.py` — HTML/CSS templates and category color maps for renderer (no LLM, just templates)

To change Claude's scoring/writing behavior, edit prompt files. To change pipeline logic, edit agent files.

### HTTP Bridge (OpenClaw Integration)

`src/server.py` — FastAPI service wrapping the pipeline:
- `GET /health` — Health check
- `POST /api/run` — Trigger full pipeline, returns structured result dict
- `run_pipeline()` in `src/main.py` — Extracted function returning dict with html_content, feishu_doc_url, etc.
- Managed as a subprocess by OpenClaw's `extensions/ai-daily/` extension

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Full pipeline
python -m src.main

# With custom params
python -m src.main --hours 48 --top-n 20

# Test individual agents (each has __main__ block)
python -m src.agents.rss_agent
python -m src.agents.prefilter
python -m src.agents.filter_agent
python -m src.agents.renderer_agent

# HTTP bridge server
python -m src.server
```

## Configuration

All secrets/config via environment variables (see `.env.example`). Required: `ANTHROPIC_API_KEY`, `FEISHU_APP_ID`, `FEISHU_APP_SECRET`. Config is centralized in `src/config.py`.

Custom RSS feeds via `RSS_FEEDS` env var (comma-separated URLs) — source names are auto-derived from URL domains via `DOMAIN_NAME_MAP` in config.

## Key Design Decisions

- Each agent is independently testable via `python -m`
- Prefilter runs before Claude API to reduce cost and improve signal-to-noise ratio
- Claude API calls use batch mode (send all articles in one request, get JSON array back)
- HTML renderer uses Python string templates, NOT Claude — for speed and consistency
- Feishu publish: Drive API uploads HTML file, Docx API creates online document; fallback to simple text if conversion fails
- Error isolation: each agent catches its own exceptions; one failing RSS source or API call doesn't kill the pipeline
- Claude API and Feishu API retries: 2 retries with 5s interval (`_call_claude_with_retry` pattern shared across filter/writer agents)
- Zero articles after filtering → log and exit cleanly, no empty report pushed
- `load_dotenv(override=True)` in config.py prevents OpenClaw env var pollution

## Code Conventions

- Type hints on all functions
- Docstrings on all functions
- No `print()` — use `logging` exclusively (via `src/utils/logger.py`)
- No hardcoded config — everything through `src/config.py`
- Output files go to `output/` directory (gitignored)
- All output (summaries, titles) in Chinese; preserve original English titles alongside translations

## Other

- `juya-news-card/` — Separate Next.js sub-project for card rendering UI (independent from the Python pipeline)
