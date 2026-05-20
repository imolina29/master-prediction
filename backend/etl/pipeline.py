import logging
from pathlib import Path

from backend.etl.downloader import download_matches_csv
from backend.etl.loader import load_matches
from backend.etl.parser import parse_matches_csv
from backend.services.teams import TeamNormalizer

logger = logging.getLogger(__name__)

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


async def run_pipeline(
    data_dir: Path = DEFAULT_DATA_DIR,
    divisions: set[str] | None = None,
) -> dict:
    logger.info("Starting ETL pipeline")

    csv_path = await download_matches_csv(data_dir)
    logger.info("Download complete: %s", csv_path)

    rows = parse_matches_csv(csv_path, divisions=divisions)
    logger.info("Parsed %d matches", len(rows))

    normalizer = TeamNormalizer()
    loaded = load_matches(rows, normalize=normalizer.normalize)
    logger.info("Loaded %d matches to database", loaded)

    return {"downloaded": True, "parsed": len(rows), "loaded": loaded}
