import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    from backend.etl.odds import run_odds_sync

    result = run_odds_sync()
    logger.info("Odds sync complete: %s", result)


if __name__ == "__main__":
    main()
