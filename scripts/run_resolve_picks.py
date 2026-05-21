import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    from backend.betting.tracker import resolve_picks

    resolved = resolve_picks()
    logger.info("Resolved %d picks", resolved)


if __name__ == "__main__":
    main()
