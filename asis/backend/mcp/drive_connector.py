"""
MCP Google Drive Connector — loads internal company documents into context.
Uses a service-account credentials file path from settings.
"""

from __future__ import annotations

import os
from pathlib import Path

from ..config import get_logger, get_settings
from .base_mcp import BaseMCP

settings = get_settings()
logger = get_logger(__name__)


class DriveConnectorMCP(BaseMCP):
    """Fetches documents from Google Drive for internal context enrichment."""

    source_name = "google_drive"

    async def fetch_document(self, file_id: str) -> str:
        """
        Download and return the text content of a Google Drive file.
        Supports: Google Docs (as plain text), PDF, plain text files.
        Falls back gracefully if credentials are not configured.
        """
        return await self._call_with_retry(self._do_fetch, file_id)

    async def list_recent(self, *, max_files: int = 10) -> str:
        """List recently modified files in the service account's Drive."""
        return await self._call_with_retry(self._do_list, max_files=max_files)

    # ── Internal ──────────────────────────────────────────────────────────

    async def _do_fetch(self, file_id: str) -> str:
        creds_path = settings.google_drive_credentials
        if not creds_path:
            return "DRIVE_UNAVAILABLE: GOOGLE_DRIVE_CREDENTIALS not configured."

        if not Path(creds_path).exists():
            return f"DRIVE_UNAVAILABLE: Credentials file not found at {creds_path}."

        try:
            from google.oauth2 import service_account  # type: ignore[import]
            from googleapiclient.discovery import build  # type: ignore[import]
            import io
        except ImportError:
            return "DRIVE_UNAVAILABLE: google-api-python-client not installed."

        scopes = ["https://www.googleapis.com/auth/drive.readonly"]
        credentials = service_account.Credentials.from_service_account_file(
            creds_path, scopes=scopes
        )

        # Run synchronously in executor (Drive SDK is sync)
        import asyncio
        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(None, _fetch_sync, credentials, file_id)
        return content

    async def _do_list(self, *, max_files: int = 10) -> str:
        creds_path = settings.google_drive_credentials
        if not creds_path:
            return "DRIVE_UNAVAILABLE: GOOGLE_DRIVE_CREDENTIALS not configured."

        try:
            from google.oauth2 import service_account  # type: ignore[import]
        except ImportError:
            return "DRIVE_UNAVAILABLE: google-api-python-client not installed."

        import asyncio

        scopes = ["https://www.googleapis.com/auth/drive.readonly"]
        credentials = service_account.Credentials.from_service_account_file(
            creds_path, scopes=scopes
        )

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _list_sync, credentials, max_files)


def _fetch_sync(credentials: object, file_id: str) -> str:
    """Synchronous Drive file fetch — run in executor."""
    from googleapiclient.discovery import build  # type: ignore[import]
    from googleapiclient.http import MediaIoBaseDownload  # type: ignore[import]
    import io

    service = build("drive", "v3", credentials=credentials)

    # Get file metadata to determine MIME type
    meta = service.files().get(fileId=file_id, fields="name,mimeType").execute()
    mime_type = meta.get("mimeType", "")

    if "google-apps.document" in mime_type:
        # Export Google Doc as plain text
        result = (
            service.files()
            .export(fileId=file_id, mimeType="text/plain")
            .execute()
        )
        return result.decode("utf-8") if isinstance(result, bytes) else str(result)
    else:
        # Download as binary and decode
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return fh.getvalue().decode("utf-8", errors="replace")[:10000]


def _list_sync(credentials: object, max_files: int) -> str:
    """Synchronous Drive file listing — run in executor."""
    from googleapiclient.discovery import build  # type: ignore[import]

    service = build("drive", "v3", credentials=credentials)
    results = (
        service.files()
        .list(
            pageSize=max_files,
            orderBy="modifiedTime desc",
            fields="files(id,name,mimeType,modifiedTime)",
        )
        .execute()
    )
    files = results.get("files", [])
    if not files:
        return "No files found in Drive."
    lines = [f"Recent Drive files ({len(files)}):"]
    for f in files:
        lines.append(f"  • [{f['id']}] {f['name']} ({f.get('modifiedTime', '')[:10]})")
    return "\n".join(lines)
