import logging
from dataclasses import asdict
from typing import Callable

from backend.db.client import get_supabase
from backend.etl.parser import MatchRow

logger = logging.getLogger(__name__)


def match_row_to_dict(row: MatchRow, normalize: Callable[[str], str]) -> dict:
    d = asdict(row)
    d["home_team"] = normalize(d["home_team"])
    d["away_team"] = normalize(d["away_team"])
    return d


def load_matches(
    rows: list[MatchRow],
    normalize: Callable[[str], str],
    batch_size: int = 500,
) -> int:
    client = get_supabase()
    total = 0

    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        records = [match_row_to_dict(r, normalize) for r in batch]

        client.table("matches").upsert(
            records,
            on_conflict="division,match_date,home_team,away_team",
        ).execute()

        total += len(batch)
        logger.info("Loaded batch %d-%d (%d total)", i, i + len(batch), total)

    return total
