# webCrawlAgent

A Python web crawling agent that renders pages in a headless Playwright browser, summarizes the site with Gemini 2.5 Flash, and produces a downloadable PDF report. A minimal chat-style UI (FastAPI) lets you enter a URL, stream crawl progress, and download the final summary.

## Features
- Headless Chromium crawling with boilerplate trimming and light multi-page traversal
- Gemini-powered summaries enriched with crawl metrics (headings, links, CTAs)
- Report builder that exports PDF summaries and exposes downloadable endpoints
- FastAPI backend with SSE-style chat updates and CLI utility for quick runs
- Configurable limits for crawl depth/token budgets via environment variables

## Getting Started
1. Create env vars:
   ```powershell
   Copy-Item .env.example .env
   # Choose an LLM provider (defaults to Gemini):
   #   $env:LLM_PROVIDER = "gemini"  # requires GEMINI_API_KEY
   #   $env:LLM_PROVIDER = "grok"    # requires GROK_API_KEY
   # Always set the matching API key + optional model names.
   ```
2. Create venv & install dependencies:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -e .[dev]
   playwright install chromium
   ```
3. Run FastAPI app:
   ```powershell
   uvicorn webcrawlagent.main:app --reload --port 8000
   ```
4. Visit http://localhost:8000 to use the chat UI. PDFs land under `reports/` with UUID filenames.

## CLI Usage
```powershell
python -m webcrawlagent.cli --url https://example.com --out reports/example.pdf
```

## LLM Providers
- `LLM_PROVIDER=gemini` (default) uses Google Gemini; set `GEMINI_API_KEY` + optional `GEMINI_MODEL`.
- `LLM_PROVIDER=grok` routes through xAI's Grok chat completions; set `GROK_API_KEY` + optional `GROK_MODEL`.
- Both providers share the same structured JSON instructions and will fall back to crawler-only summaries if the API blocks the content.