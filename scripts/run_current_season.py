"""Fetch finished match results for the current season from football-data.org."""

import logging

from backend.etl.fixtures import run_current_season_sync

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    result = run_current_season_sync()
    logger.info(
        "Current season %d: %d match results loaded",
        result["season"],
        result["total_results"],
    )


if __name__ == "__main__":
    main()
