"""FastAPI application for Redrob Candidate Ranker."""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from inferencer import batch_llm_inference
from output import full_csv_bytes, submission_csv_bytes
from ranker import finalize_rank_results, load_candidates, rank_candidates
from schema import load_schema, validate_candidate

APP_DIR = Path(__file__).parent
STATIC_DIR = APP_DIR / "static"
DEFAULT_JD_PATH = APP_DIR / "default_jd.txt"
SAMPLE_PATH = APP_DIR.parent.parent / "sample_candidates.json"

app = FastAPI(title="Redrob Candidate Ranker", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

jobs: dict[str, dict[str, Any]] = {}
uploads: dict[str, list[dict[str, Any]]] = {}


def _load_default_jd() -> str:
    if DEFAULT_JD_PATH.exists():
        return DEFAULT_JD_PATH.read_text(encoding="utf-8")
    parent = APP_DIR.parent.parent / "job_description.txt"
    if parent.exists():
        return parent.read_text(encoding="utf-8")
    return ""


def _parse_candidates(content: bytes, filename: str, tmp_path: Path) -> list[dict[str, Any]]:
    if filename.endswith(".json"):
        data = json.loads(content.decode("utf-8"))
        records = data if isinstance(data, list) else [data]
        for i, record in enumerate(records, start=1):
            errors = validate_candidate(record, line_no=i)
            if errors:
                raise ValueError(errors[0])
        return records
    return load_candidates(tmp_path)


async def _run_ranking_job(
    job_id: str,
    candidates: list[dict[str, Any]],
    job_description: str,
    top_k: int,
    use_llm: bool,
) -> None:
    job = jobs[job_id]

    def progress(pct: float, msg: str) -> None:
        job["progress"] = pct
        job["message"] = msg
        job["processed"] = int(pct * job.get("total_candidates", 0))

    try:
        scored, stats = rank_candidates(
            candidates,
            job_description,
            top_k=top_k,
            progress_callback=progress,
            use_llm=False,
        )
        job["stats"] = stats

        # Optional LLM enrichment - only if API key is available and use_llm=True
        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
        if use_llm and api_key:
            progress(0.85, "Running AI inference on top 200...")
            llm_limit = min(200, len(scored))
            enriched = await batch_llm_inference(scored[:llm_limit], job_description, api_key=api_key)
            rest = scored[llm_limit:]
            scored = enriched + rest
            scored.sort(key=lambda x: (-round(x["score"], 4), x["candidate_id"]))
        else:
            progress(0.88, "Finalizing rankings with base scores...")

        results = finalize_rank_results(scored, top_k=top_k, progress_callback=progress)
        job["results"] = results
        job["stats"]["shortlisted"] = len(results)
        job["status"] = "completed"
        job["progress"] = 1.0
        job["message"] = f"Complete — {len(results)} candidates ranked"
        job["completed_at"] = datetime.utcnow().isoformat()
    except Exception as exc:
        job["status"] = "failed"
        job["message"] = str(exc)
        job["progress"] = 0.0


@app.get("/health")
@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "redrob-ranker"}


@app.get("/api/default-jd")
async def get_default_jd() -> dict[str, str]:
    return {"job_description": _load_default_jd()}


@app.get("/api/schema")
async def get_schema() -> dict[str, Any]:
    schema = load_schema()
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")
    return schema


@app.post("/api/upload")
async def upload_candidates(candidates_file: UploadFile = File(...)) -> dict[str, str]:
    content = await candidates_file.read()
    filename = candidates_file.filename or "candidates.jsonl"
    upload_id = str(uuid.uuid4())

    tmp_dir = APP_DIR / "tmp"
    tmp_dir.mkdir(exist_ok=True)
    tmp_path = tmp_dir / f"{upload_id}_{filename}"
    tmp_path.write_bytes(content)

    try:
        candidates = _parse_candidates(content, filename, tmp_path)
    except Exception as exc:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    uploads[upload_id] = candidates
    return {"upload_id": upload_id, "count": len(candidates)}


@app.post("/api/rank")
async def start_ranking(
    background_tasks: BackgroundTasks,
    job_description: str = Form(""),
    top_k: int = Form(100),
    use_llm: bool = Form(True),
    upload_id: str = Form(""),
    candidates_file: UploadFile | None = File(None),
) -> dict[str, str]:
    jd = job_description or _load_default_jd()
    candidates: list[dict[str, Any]]

    if upload_id and upload_id in uploads:
        candidates = uploads[upload_id]
    elif candidates_file:
        content = await candidates_file.read()
        filename = candidates_file.filename or "candidates.jsonl"
        tmp_dir = APP_DIR / "tmp"
        tmp_dir.mkdir(exist_ok=True)
        tmp_path = tmp_dir / f"{uuid.uuid4()}_{filename}"
        tmp_path.write_bytes(content)
        try:
            candidates = _parse_candidates(content, filename, tmp_path)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        finally:
            tmp_path.unlink(missing_ok=True)
    else:
        raise HTTPException(status_code=400, detail="Provide upload_id or candidates_file")

    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "job_id": job_id,
        "status": "running",
        "progress": 0.0,
        "message": "Starting ranking...",
        "total_candidates": len(candidates),
        "processed": 0,
        "created_at": datetime.utcnow().isoformat(),
        "completed_at": None,
        "results": None,
        "stats": {},
    }

    background_tasks.add_task(
        _run_ranking_job, job_id, candidates, jd, min(top_k, len(candidates)), use_llm
    )
    return {"job_id": job_id}


@app.post("/api/rank-sample")
async def rank_sample(background_tasks: BackgroundTasks, use_llm: bool = Form(True)) -> dict[str, str]:
    if not SAMPLE_PATH.exists():
        raise HTTPException(status_code=404, detail="sample_candidates.json not found")
    candidates = load_candidates(SAMPLE_PATH)
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "job_id": job_id,
        "status": "running",
        "progress": 0.0,
        "message": "Ranking sample dataset...",
        "total_candidates": len(candidates),
        "processed": 0,
        "created_at": datetime.utcnow().isoformat(),
        "completed_at": None,
        "results": None,
        "stats": {},
    }
    background_tasks.add_task(
        _run_ranking_job, job_id, candidates, _load_default_jd(), min(100, len(candidates)), use_llm
    )
    return {"job_id": job_id, "count": len(candidates)}


@app.get("/api/status/{job_id}")
async def get_status(job_id: str) -> dict[str, Any]:
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    job = jobs[job_id]
    return {
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"],
        "message": job["message"],
        "total_candidates": job.get("total_candidates", 0),
        "processed": job.get("processed", 0),
        "stats": job.get("stats", {}),
        "created_at": job.get("created_at"),
        "completed_at": job.get("completed_at"),
    }


@app.get("/api/results/{job_id}")
async def get_results(job_id: str) -> dict[str, Any]:
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    job = jobs[job_id]
    if job["status"] != "completed":
        raise HTTPException(status_code=202, detail="Job still running")
    return {
        "job_id": job_id,
        "stats": job.get("stats", {}),
        "total_candidates": job.get("total_candidates", 0),
        "results": [
            {
                "candidate_id": r["candidate_id"],
                "rank": r["rank"],
                "score": r["score"],
                "reasoning": r["reasoning"],
                "profile": r["candidate"].get("profile", {}),
                "signals": r["candidate"].get("redrob_signals", {}),
                "breakdown": r["breakdown"],
            }
            for r in job["results"]
        ],
    }


@app.get("/api/download/{job_id}")
async def download_csv(job_id: str, format: str = "full") -> Response:
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    job = jobs[job_id]
    if job["status"] != "completed":
        raise HTTPException(status_code=202, detail="Job still running")

    if format == "hackathon":
        content = submission_csv_bytes(job["results"])
        fname = f"submission_{job_id[:8]}.csv"
    else:
        content = full_csv_bytes(job["results"])
        fname = f"redrob_ranking_{job_id[:8]}.csv"

    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


# Legacy route aliases
@app.get("/api/rank/{job_id}/status")
async def legacy_status(job_id: str) -> dict[str, Any]:
    return await get_status(job_id)


@app.get("/api/rank/{job_id}/results")
async def legacy_results(job_id: str) -> dict[str, Any]:
    return await get_results(job_id)


@app.get("/api/rank/{job_id}/download")
async def legacy_download(job_id: str) -> Response:
    return await download_csv(job_id)


if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str) -> FileResponse:
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        fp = STATIC_DIR / full_path
        if fp.is_file():
            return FileResponse(fp)
        return FileResponse(STATIC_DIR / "index.html")
