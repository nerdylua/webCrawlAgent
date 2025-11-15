from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
from sse_starlette.sse import EventSourceResponse

from webcrawlagent.app.dependencies import get_service
from webcrawlagent.app.service import CrawlAgentService, ServiceResult
from webcrawlagent.config import get_settings

router = APIRouter(prefix="/api", tags=["agent"])


class AnalyzeRequest(BaseModel):
    url: HttpUrl


class AnalyzeResponse(BaseModel):
    url: HttpUrl
    summary: dict
    metrics: dict
    pdf_path: str


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    request: AnalyzeRequest, service: CrawlAgentService = Depends(get_service)  # noqa: B008
):
    try:
        result = await service.run(str(request.url))
    except Exception as exc:  # pragma: no cover - network/LLM errors
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return _serialize_result(result)


@router.get("/stream")
async def stream(
    url: HttpUrl = Query(..., description="Website to analyze"),  # noqa: B008
    service: CrawlAgentService = Depends(get_service),  # noqa: B008
):
    async def event_generator():
        queue: asyncio.Queue[dict] = asyncio.Queue()

        async def progress(message: str):
            await queue.put({"type": "status", "message": message})

        task = asyncio.create_task(service.run(str(url), progress))

        while True:
            if task.done() and queue.empty():
                break
            try:
                event = await asyncio.wait_for(queue.get(), timeout=0.2)
                yield {"event": "message", "data": json.dumps(event)}
            except TimeoutError:
                if task.done():
                    break

        try:
            result = await task
        except Exception as exc:  # pragma: no cover
            yield {"event": "message", "data": json.dumps({"type": "error", "message": str(exc)})}
            return
        summary_payload = {"type": "summary", **_serialize_result(result)}
        yield {"event": "message", "data": json.dumps(summary_payload)}

    return EventSourceResponse(event_generator())


def _serialize_result(result: ServiceResult) -> dict:
    file_name = Path(result.pdf_path).name
    return {
        "url": result.url,
        "summary": {
            "overview": result.summary.overview,
            "sections": result.summary.sections,
            "highlights": result.summary.highlights,
            "recommendations": result.summary.recommendations,
        },
        "metrics": asdict(result.analysis),
        "pdf_path": f"/api/reports/{file_name}",
    }


@router.get("/reports/{file_name}")  # pragma: no cover - exercised via UI/manual tests
async def download_report(file_name: str):
    settings = get_settings()
    report_dir = settings.ensure_report_dir()
    safe_path = (report_dir / file_name).resolve()
    if not str(safe_path).startswith(str(report_dir.resolve())) or not safe_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(safe_path, media_type="application/pdf", filename=file_name)
