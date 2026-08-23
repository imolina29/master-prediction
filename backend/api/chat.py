"""POST /api/chat — AI advisor endpoint."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.api.auth import require_api_key

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []
    context: dict = {}
    known_teams: list[str] = []


class ChatResponse(BaseModel):
    response: str
    context: dict


@router.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, _client: str = Depends(require_api_key)):
    from backend.advisor.engine import get_response
    from backend.db.client import get_supabase

    supabase = get_supabase()
    known = req.known_teams if req.known_teams else []
    response_text, new_ctx = get_response(supabase, req.message, known, req.context)
    return ChatResponse(response=response_text, context=new_ctx)
