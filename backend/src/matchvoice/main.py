"""FastAPI app. Serves the API and, in production, the compiled Vue frontend."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from matchvoice import __version__
from matchvoice.api.matches import router as matches_router

app = FastAPI(
    title="MatchVoice API",
    version=__version__,
    description="Synthetic football events turned into live, explainable and personalised match narration.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(matches_router)

# In the container the built frontend sits next to the backend (see Dockerfile).
_static = Path(os.environ.get("FRONTEND_DIST", Path(__file__).resolve().parents[3] / "frontend" / "dist"))
if _static.is_dir():
    app.mount("/", StaticFiles(directory=_static, html=True), name="frontend")
