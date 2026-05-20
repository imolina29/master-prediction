import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main():
    from backend.etl.understat import scrape_all

    current_only = "--current" in sys.argv
    if current_only:
        result = scrape_all(start_season=2024, end_season=2024)
    else:
        result = scrape_all()

    logging.info("Understat scrape result: %s", result)
    if result["loaded"] == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
