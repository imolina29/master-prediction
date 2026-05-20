import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from backend.etl.downloader import download_matches_csv


def test_download_creates_file(tmp_path):
    csv_content = b"Division,MatchDate,HomeTeam\nE0,2024-01-01,Arsenal\n"

    with patch("backend.etl.downloader.httpx.AsyncClient") as mock_client_cls:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.content = csv_content
        mock_response.raise_for_status = lambda: None

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        output = asyncio.run(download_matches_csv(tmp_path))

        assert output.exists()
        assert output.read_bytes() == csv_content


def test_download_raises_on_failure(tmp_path):
    with patch("backend.etl.downloader.httpx.AsyncClient") as mock_client_cls:
        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_response.raise_for_status = AsyncMock(side_effect=Exception("404 Not Found"))

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        with pytest.raises(Exception):
            asyncio.run(download_matches_csv(tmp_path))
