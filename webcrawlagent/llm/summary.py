from __future__ import annotations

import json
import logging
from typing import Any

from webcrawlagent.crawler.analyzer import AnalysisSummary
from webcrawlagent.crawler.extractor import CrawlResult
from webcrawlagent.report.models import SiteSummary

logger = logging.getLogger(__name__)

SUMMARY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "overview": {"type": "string"},
        "sections": {"type": "array", "items": {"type": "string"}},
        "highlights": {"type": "array", "items": {"type": "string"}},
        "recommendations": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["overview", "sections", "highlights", "recommendations"],
}


def build_summary_prompt(
    crawl: CrawlResult, analysis: AnalysisSummary, max_tokens: int
) -> str:
    content_chunks = crawl.aggregate_text(max_tokens)
    context = "\n\n".join(content_chunks)
    summary_metadata = json.dumps(
        {
            "root_url": analysis.root_url,
            "pages": analysis.page_summaries,
            "keywords": analysis.keywords,
            "cta_links": analysis.ctas,
        },
        ensure_ascii=False,
    )
    instructions = (
        "You are an analyst generating a concise website briefing. "
        "Blend the structured metadata with the raw text to produce actionable insight."
    )
    return (
        f"{instructions}\n"
        "Return **only** JSON with the following shape:\n"
        "{\n"
        '  "overview": <2-3 sentence synopsis>,\n'
        '  "sections": [list of key sections and their purpose],\n'
        '  "highlights": [bullet-level product/features/metrics insights],\n'
        '  "recommendations": [next actions or opportunities]\n'
        "}\n"
        f"Metadata: {summary_metadata}\n"
        "Content: \n"
        f"{context}"
    )


def build_fallback_summary(
    crawl: CrawlResult, analysis: AnalysisSummary, *, reason: str
) -> SiteSummary:
    """Construct a deterministic summary when an LLM output is unavailable."""
    sections: list[str] = []
    for page in analysis.page_summaries[:3]:
        snippet = (
            page.get("description")
            or " / ".join(page.get("headings", []))
            or f"{page.get('word_count', 0)} words (status {page.get('status')})"
        )
        sections.append(f"{page.get('title')}: {snippet}")

    if not sections and crawl.pages:
        first_page = crawl.pages[0]
        sections.append(f"{first_page.title or first_page.url}: {first_page.description}")

    highlights: list[str] = []
    if analysis.keywords:
        highlights.append("Top keywords: " + ", ".join(analysis.keywords[:6]))
    highlights.append(
        f"Internal links: {analysis.internal_links} · External links: {analysis.external_links}"
    )
    if analysis.ctas:
        highlights.append("Detected CTAs: " + ", ".join(analysis.ctas[:5]))

    recommendations = [
        "Review the crawler output manually because the LLM blocked the content.",
        "Retry with sanitized text or a different site if you need an AI-authored summary.",
    ]

    overview = (
        f"Crawled {analysis.total_pages} page(s) from {analysis.root_url}. "
        f"LLM output unavailable ({reason}); showing crawler-derived summary."
    )

    logger.warning("Using fallback summary because %s", reason)
    return SiteSummary(
        overview=overview,
        sections=sections or [analysis.root_url],
        highlights=highlights,
        recommendations=recommendations,
    )

