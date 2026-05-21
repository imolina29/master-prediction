import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    from backend.etl.fixtures import run_fixtures_sync

    logger.info("Starting fixtures sync from football-data.org")
    result = run_fixtures_sync()
    logger.info(
        "Fixtures sync complete: %d fixtures loaded, %d national teams with features",
        result["total_fixtures"],
        result["national_teams_with_features"],
    )


if __name__ == "__main__":
    main()
