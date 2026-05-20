import logging
from pathlib import Path

import httpx

MATCHES_URL = (
    "https://raw.githubusercontent.com/xgabora/"
    "Club-Football-Match-Data-2000-2025/main/data/Matches.csv"
)

logger = logging.getLogger(__name__)


async def download_matches_csv(dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    output_path = dest_dir / "Matches.csv"

    async with httpx.AsyncClient(timeout=120.0) as client:
        logger.info("Downloading matches CSV from %s", MATCHES_URL)
        response = await client.get(MATCHES_URL)
        response.raise_for_status()

    output_path.write_bytes(response.content)
    size_mb = len(response.content) / (1024 * 1024)
    logger.info("Downloaded %.1f MB to %s", size_mb, output_path)
    return output_path
