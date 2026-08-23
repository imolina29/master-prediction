"""POST /api/performance — calculate betting performance metrics."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.api.auth import require_api_key

router = APIRouter()


class PerformanceRequest(BaseModel):
    resolved_picks: list[dict]


class PerformanceResponse(BaseModel):
    total_picks: int
    wins: int
    losses: int
    profit: float
    roi: float
    hit_rate: float
    by_market: dict


@router.post("/api/performance", response_model=PerformanceResponse)
async def performance(req: PerformanceRequest, _client: str = Depends(require_api_key)):
    from backend.betting.tracker import calculate_performance

    result = calculate_performance(req.resolved_picks)
    return PerformanceResponse(**result)
