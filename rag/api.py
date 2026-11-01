"""HTTP surface: POST /ask, GET /health, and the one-page UI at /. The pipeline is rebuilt when `bm25.json` changes on
disk, so running `ingest` while the server is up takes effect on the next request."""
from __future__ import annotations

import logging
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from rag.documents import COLLECTIONS
from rag.pipeline import Pipeline
from rag.settings import Settings

log = logging.getLogger("rag.api")


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    alpha: float | None = Field(default=None, ge=0.0, le=1.0)
    collection: str | None = None
    top_k: int | None = Field(default=None, ge=1, le=20)


def create_app(settings: Settings | None = None, pipeline: Pipeline | None = None) -> FastAPI:
    s = settings or Settings()
    app = FastAPI(title="Enterprise search RAG demo", version="0.1.0")
    bm25_path = Path(s.index_dir) / "bm25.json"
    state = {"pipeline": pipeline, "stamp": bm25_path.stat().st_mtime_ns if bm25_path.exists() else None}

    def pipe() -> Pipeline:
        stamp = bm25_path.stat().st_mtime_ns if bm25_path.exists() else None
        if state["pipeline"] is None or stamp != state["stamp"]:
            if state["pipeline"] is not None:
                log.info("index changed on disk: reloading the pipeline")
            state["pipeline"], state["stamp"] = Pipeline(s), stamp
        return state["pipeline"]

    @app.get("/health")
    def health() -> dict:
        try:
            p = pipe()
            n = p.store.count()
        except Exception as err:    # noqa: BLE001 - a missing index or key is a health fact, not a crash; the message is ours, not the SDK's
            return {"status": "degraded", "error": type(err).__name__ + ": " + str(err)[:200], **s.describe()}
        return {"status": "ok" if n else "empty", "chunks": n, "vocab": len(p.bm25.vocab), "warning": p.index_warning, **s.describe()}

    @app.post("/ask")
    def ask(req: AskRequest) -> JSONResponse:
        if req.collection not in (None, *COLLECTIONS):
            raise HTTPException(status_code=422, detail=f"unknown collection; expected one of {COLLECTIONS}")
        try:
            a = pipe().ask(req.question, alpha=req.alpha, top_k=req.top_k, collection=req.collection)
        except RuntimeError as err:
            raise HTTPException(status_code=409, detail=str(err)) from err
        except Exception as err:    # noqa: BLE001 - SDK errors can carry key fragments in their message: log the type, return a generic detail
            log.error("ask failed: %s", type(err).__name__)
            raise HTTPException(status_code=502, detail=f"retrieval or generation failed ({type(err).__name__}); see the server log") from err
        return JSONResponse(asdict(a))

    @app.get("/")
    def index():
        page = Path(s.static_dir) / "index.html"
        if not page.exists():
            raise HTTPException(status_code=404, detail="static/index.html missing")
        return FileResponse(page)

    return app
