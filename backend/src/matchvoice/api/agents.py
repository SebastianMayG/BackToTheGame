"""POST /api/matches/{seed}/ask and /query: the two agents that call the match-data tools."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from matchvoice.agents.analyst_query import query as run_query
from matchvoice.agents.live import is_configured
from matchvoice.agents.qa import ask as run_ask
from matchvoice.models import AskRequest, AskResponse, QueryRequest, QueryResponse

router = APIRouter(prefix="/api", tags=["agents"])

_slots = asyncio.Semaphore(4)  # model calls at once across all viewers


async def _run(fn, *args):  # type: ignore[no-untyped-def]
    if not is_configured():
        raise HTTPException(503, "AI agents are not configured")
    if _slots.locked():
        raise HTTPException(429, "The agents are busy, try again in a moment")
    async with _slots:
        try:
            return await asyncio.to_thread(fn, *args)
        except ValueError as exc:  # unknown club in the request
            raise HTTPException(400, str(exc)) from exc
        except Exception as exc:  # network, auth, quota
            raise HTTPException(502, f"Agent failed: {str(exc)[:200]}") from exc


@router.post("/matches/{seed}/ask", response_model=AskResponse)
async def ask(seed: int, req: AskRequest) -> AskResponse:
    """Chat Q&A: a question about the match so far, answered with data from the MCP tools."""
    return await _run(run_ask, req, seed)


@router.post("/matches/{seed}/query", response_model=QueryResponse)
async def query(seed: int, req: QueryRequest) -> QueryResponse:
    """Analyst Query: a request in natural language, answered with an OverlaySpec for the pitch."""
    return await _run(run_query, req, seed)
