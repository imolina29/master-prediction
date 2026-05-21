import logging

from supabase import Client

logger = logging.getLogger(__name__)


def fetch_all(client: Client, table_name: str, page_size: int = 1000) -> list[dict]:
    all_data: list[dict] = []
    offset = 0
    while True:
        resp = client.table(table_name).select("*").range(offset, offset + page_size - 1).execute()
        all_data.extend(resp.data)
        if len(resp.data) < page_size:
            break
        offset += page_size
    logger.info("Fetched %d rows from %s", len(all_data), table_name)
    return all_data
