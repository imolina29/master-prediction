"""Public API router — no authentication required."""

import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from backend.api.public.data import (
    get_accuracy_stats,
    get_h2h,
    get_match_elo,
    get_team_features,
)
from backend.api.public.slugs import (
    DIVISION_DISPLAY,
    DIVISION_FLAGS,
    DIVISION_SLUGS,
    SLUG_TO_DIVISION,
    deslugify_team,
    slugify_team,
)
from webapp.data import get_supabase_client, get_track_record

router = APIRouter(prefix="/api/public")

_INTERNAL_KEY = os.environ.get("INTERNAL_API_KEY", "")
_RATE_COUNTS: dict[str, list[float]] = {}
_RATE_LIMIT = 60
_RATE_WINDOW = 60.0


def _check_rate_limit(request: Request) -> bool:
    if _INTERNAL_KEY and request.headers.get("X-Internal-Key") == _INTERNAL_KEY:
        return True
    ip = request.client.host if request.client else "unknown"
    now = datetime.now(timezone.utc).timestamp()
    hits = _RATE_COUNTS.get(ip, [])
    hits = [t for t in hits if now - t < _RATE_WINDOW]
    if len(hits) >= _RATE_LIMIT:
        return False
    hits.append(now)
    _RATE_COUNTS[ip] = hits
    return True


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/predictions/upcoming")
async def predictions_upcoming(request: Request):
    if not _check_rate_limit(request):
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
    client = get_supabase_client()
    col_tz = timezone(timedelta(hours=-5))
    now_col = datetime.now(col_tz)
    today = now_col.strftime("%Y-%m-%d")
    end = (now_col + timedelta(days=21)).strftime("%Y-%m-%d")
    resp = (
        client.table("predictions")
        .select("*")
        .gte("match_date", today)
        .lte("match_date", end)
        .order("match_date")
        .limit(100)
        .execute()
    )
    predictions = resp.data or []
    for p in predictions:
        p["home_slug"] = slugify_team(p["home_team"])
        p["away_slug"] = slugify_team(p["away_team"])
        p["match_slug"] = f"{slugify_team(p['home_team'])}-vs-{slugify_team(p['away_team'])}"
        p["league_slug"] = DIVISION_SLUGS.get(p.get("division", ""), "")
        p["league_name"] = DIVISION_DISPLAY.get(p.get("division", ""), "")
        p["league_flag"] = DIVISION_FLAGS.get(p.get("division", ""), "")
    return {"predictions": predictions}


@router.get("/predictions/stats")
async def predictions_stats(request: Request):
    if not _check_rate_limit(request):
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
    return get_accuracy_stats()


@router.get("/predictions/track-record")
async def predictions_track_record(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    division: str | None = Query(None),
    confidence: str | None = Query(None),
):
    if not _check_rate_limit(request):
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
    tr = get_track_record(limit=5000)
    if tr.empty:
        return {"predictions": [], "page": page, "total": 0, "pages": 0}
    if division:
        tr = tr[tr["division"] == division]
    if confidence:
        tr = tr[tr["confidence"] == confidence]
    total = len(tr)
    start = (page - 1) * per_page
    end = start + per_page
    page_data = tr.iloc[start:end]
    predictions = []
    for _, row in page_data.iterrows():
        p = row.to_dict()
        for k, v in p.items():
            if hasattr(v, "item"):
                p[k] = v.item()
        p["correct"] = p.get("predicted_result") == p.get("ft_result")
        predictions.append(p)
    return {
        "predictions": predictions,
        "page": page,
        "total": total,
        "pages": (total + per_page - 1) // per_page,
    }


@router.get("/match/{date}/{slug}")
async def match_detail(request: Request, date: str, slug: str, division: str | None = Query(None)):
    if not _check_rate_limit(request):
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
    parts = slug.split("-vs-")
    if len(parts) != 2:
        raise HTTPException(status_code=404, detail="Invalid match slug")
    home_slug, away_slug = parts[0], parts[1]
    home_name = deslugify_team(home_slug, division)
    away_name = deslugify_team(away_slug, division)
    if not home_name or not away_name:
        raise HTTPException(status_code=404, detail="Team not found")

    client = get_supabase_client()
    pred_resp = (
        client.table("predictions")
        .select("*")
        .eq("match_date", date)
        .eq("home_team", home_name)
        .eq("away_team", away_name)
        .limit(1)
        .execute()
    )
    if not pred_resp.data:
        raise HTTPException(status_code=404, detail="Prediction not found")

    prediction = pred_resp.data[0]
    div = prediction.get("division", division or "")

    home_features = get_team_features(home_name, div)
    away_features = get_team_features(away_name, div)
    elo = get_match_elo(date, home_name, away_name)
    h2h = get_h2h(home_name, away_name)

    ventajas = _build_ventajas(home_name, away_name, home_features, away_features, elo)

    return {
        "prediction": prediction,
        "home_features": home_features,
        "away_features": away_features,
        "elo": {"home": elo[0], "away": elo[1]} if elo else None,
        "h2h": h2h,
        "ventajas": ventajas,
        "league_name": DIVISION_DISPLAY.get(div, ""),
        "league_flag": DIVISION_FLAGS.get(div, ""),
        "league_slug": DIVISION_SLUGS.get(div, ""),
    }


@router.get("/league/{league_slug}/upcoming")
async def league_upcoming(request: Request, league_slug: str):
    if not _check_rate_limit(request):
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
    division = SLUG_TO_DIVISION.get(league_slug)
    if not division:
        raise HTTPException(status_code=404, detail="League not found")

    client = get_supabase_client()
    col_tz = timezone(timedelta(hours=-5))
    now_col = datetime.now(col_tz)
    today = now_col.strftime("%Y-%m-%d")
    end = (now_col + timedelta(days=21)).strftime("%Y-%m-%d")
    resp = (
        client.table("predictions")
        .select("*")
        .eq("division", division)
        .gte("match_date", today)
        .lte("match_date", end)
        .order("match_date")
        .limit(50)
        .execute()
    )
    predictions = resp.data or []
    for p in predictions:
        p["match_slug"] = f"{slugify_team(p['home_team'])}-vs-{slugify_team(p['away_team'])}"

    return {
        "league": {
            "code": division,
            "slug": league_slug,
            "name": DIVISION_DISPLAY.get(division, ""),
            "flag": DIVISION_FLAGS.get(division, ""),
        },
        "predictions": predictions,
    }


def _build_ventajas(
    home_name: str,
    away_name: str,
    home_f: dict | None,
    away_f: dict | None,
    elo: tuple[float, float] | None,
) -> dict:
    home_bullets: list[str] = []
    away_bullets: list[str] = []

    if not home_f or not away_f:
        return {"home": home_bullets, "away": away_bullets}

    h_gsa = home_f.get("goals_scored_avg")
    a_gsa = away_f.get("goals_scored_avg")
    if h_gsa is not None and a_gsa is not None:
        if h_gsa - a_gsa > 0.3:
            home_bullets.append(
                f"{home_name} promedia {h_gsa:.1f} goles por partido vs {a_gsa:.1f}"
            )
        elif a_gsa - h_gsa > 0.3:
            away_bullets.append(
                f"{away_name} promedia {a_gsa:.1f} goles por partido vs {h_gsa:.1f}"
            )

    h_gca = home_f.get("goals_conceded_avg")
    a_gca = away_f.get("goals_conceded_avg")
    if h_gca is not None and a_gca is not None:
        if a_gca - h_gca > 0.3:
            home_bullets.append(
                f"{home_name} tiene mejor defensa ({h_gca:.1f} goles recibidos vs {a_gca:.1f})"
            )
        elif h_gca - a_gca > 0.3:
            away_bullets.append(
                f"{away_name} tiene mejor defensa ({a_gca:.1f} goles recibidos vs {h_gca:.1f})"
            )

    h_wr = home_f.get("win_rate")
    a_wr = away_f.get("win_rate")
    if h_wr is not None and a_wr is not None:
        if h_wr - a_wr > 0.15:
            home_bullets.append(
                f"{home_name} gana el {h_wr * 100:.0f}% de sus partidos vs {a_wr * 100:.0f}%"
            )
        elif a_wr - h_wr > 0.15:
            away_bullets.append(
                f"{away_name} gana el {a_wr * 100:.0f}% de sus partidos vs {h_wr * 100:.0f}%"
            )

    h_xg = home_f.get("xg_diff_avg")
    a_xg = away_f.get("xg_diff_avg")
    if h_xg is not None and a_xg is not None:
        if h_xg - a_xg > 0.3:
            home_bullets.append(
                f"{home_name} tiene mejor diferencia de xG ({h_xg:+.2f} vs {a_xg:+.2f})"
            )
        elif a_xg - h_xg > 0.3:
            away_bullets.append(
                f"{away_name} tiene mejor diferencia de xG ({a_xg:+.2f} vs {h_xg:+.2f})"
            )

    if elo:
        diff = elo[0] - elo[1]
        if diff > 50:
            home_bullets.append(f"{home_name} tiene ELO superior ({elo[0]:.0f} vs {elo[1]:.0f})")
        elif diff < -50:
            away_bullets.append(f"{away_name} tiene ELO superior ({elo[1]:.0f} vs {elo[0]:.0f})")

    h_vwr = home_f.get("venue_win_rate")
    if h_vwr is not None and h_vwr > 0.6:
        home_bullets.append(f"{home_name} gana el {h_vwr * 100:.0f}% de sus partidos en casa")

    return {"home": home_bullets[:3], "away": away_bullets[:3]}
