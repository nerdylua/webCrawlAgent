from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from webcrawlagent.crawler.analyzer import AnalysisSummary


@dataclass(slots=True)
class SiteSummary:
    overview: str
    sections: list[str]
    highlights: list[str]
    recommendations: list[str]

    @classmethod
    def from_llm_payload(cls, payload: dict) -> SiteSummary:
        return cls(
            overview=payload.get("overview", ""),
            sections=payload.get("sections", []),
            highlights=payload.get("highlights", []),
            recommendations=payload.get("recommendations", []),
        )


@dataclass(slots=True)
class ReportPayload:
    url: str
    summary: SiteSummary
    metrics: AnalysisSummary
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    pdf_path: str | None = None
