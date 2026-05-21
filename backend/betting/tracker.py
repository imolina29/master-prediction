import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def resolve_single_pick(pick: dict, match: dict) -> dict:
    market = pick["market"]
    selection = pick["selection"]
    odd = pick["odd"]
    stake = pick["stake"]

    won = False
    if market.startswith("1x2"):
        won = selection == match["ft_result"]
    elif market == "over25":
        total = match["ft_home_goals"] + match["ft_away_goals"]
        won = total > 2.5
    elif market == "under25":
        total = match["ft_home_goals"] + match["ft_away_goals"]
        won = total <= 2.5

    result = "win" if won else "loss"
    profit = stake * (odd - 1) if won else -stake

    return {"result": result, "profit": profit}


def resolve_picks() -> int:
    from backend.db.client import get_supabase

    client = get_supabase()

    pending = client.table("value_bets").select("*").is_("result", "null").execute()

    if not pending.data:
        logger.info("No pending picks to resolve")
        return 0

    resolved_count = 0
    for pick in pending.data:
        match_resp = (
            client.table("matches")
            .select("ft_result, ft_home_goals, ft_away_goals")
            .eq("division", pick["division"])
            .eq("match_date", pick["match_date"])
            .eq("home_team", pick["home_team"])
            .eq("away_team", pick["away_team"])
            .not_.is_("ft_result", "null")
            .execute()
        )

        if not match_resp.data:
            continue

        match = match_resp.data[0]
        resolution = resolve_single_pick(pick, match)

        client.table("value_bets").update(
            {
                "result": resolution["result"],
                "profit": resolution["profit"],
                "resolved_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", pick["id"]).execute()

        resolved_count += 1
        logger.info(
            "Resolved: %s vs %s [%s] → %s (%.2f u)",
            pick["home_team"],
            pick["away_team"],
            pick["selection"],
            resolution["result"],
            resolution["profit"],
        )

    logger.info("Resolved %d picks", resolved_count)
    return resolved_count


def calculate_performance(resolved: list[dict]) -> dict:
    if not resolved:
        return {
            "total_picks": 0,
            "wins": 0,
            "losses": 0,
            "profit": 0,
            "roi": 0,
            "hit_rate": 0,
            "by_market": {},
        }

    wins = sum(1 for r in resolved if r["result"] == "win")
    losses = sum(1 for r in resolved if r["result"] == "loss")
    total_profit = sum(r["profit"] for r in resolved)
    total_stake = sum(r["stake"] for r in resolved)

    market_groups: dict[str, list[dict]] = {}
    for r in resolved:
        market = r["market"]
        group = "1x2" if market.startswith("1x2") else "over_under"
        market_groups.setdefault(group, []).append(r)

    by_market = {}
    for group, items in market_groups.items():
        g_wins = sum(1 for i in items if i["result"] == "win")
        g_stake = sum(i["stake"] for i in items)
        g_profit = sum(i["profit"] for i in items)
        by_market[group] = {
            "picks": len(items),
            "wins": g_wins,
            "profit": round(g_profit, 2),
            "roi": round(g_profit / g_stake * 100, 2) if g_stake else 0,
        }

    return {
        "total_picks": len(resolved),
        "wins": wins,
        "losses": losses,
        "profit": round(total_profit, 2),
        "roi": round(total_profit / total_stake * 100, 2) if total_stake else 0,
        "hit_rate": round(wins / len(resolved), 4),
        "by_market": by_market,
    }
