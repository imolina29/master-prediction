import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main():
    from backend.etl.pipeline import run_pipeline

    result = asyncio.run(run_pipeline())
    logging.info("Pipeline result: %s", result)
    if result["loaded"] == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
