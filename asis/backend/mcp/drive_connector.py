"""
ASIS v3.0 — Google Drive MCP connector.
Loads internal company documents into agent context via Google Drive API v3.
Uses a service-account credentials file from settings.
All failures return DATA_UNAVAILABLE — never raises.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from asis.backend.config.logging import get_logger
from asis.backend.config.settings import get_settings
from asis.backend.mcp.base_mcp import BaseMCP

logger = get_logger(__name__)

_DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
_MAX_CONTENT_CHARS = 10_000


class DriveConnectorMCP(BaseMCP):
    """
    Fetches documents from Google Drive for internal context enrichment.

    Supports Google Docs (exported as plain text), plain text files, and PDFs.
    Requires a service-account JSON credentials file whose path is configured
    via the ``google_drive_credentials`` setting.

    Usage
    -----
    mcp = DriveConnectorMCP()
    docs = await mcp.fetch_documents("Q3 strategy deck", folder_id="1AbCdEfG...")
    """

    source_name = "google_drive"

    async def fetch_documents(self, query: str, folder_id: str = "") -> str:
        """
        Search Google Drive for documents matching *query* and return their
        combined text content, suitable for injection into an LLM prompt.

        Parameters
        ----------
        query : str
            Free-text search string (passed to the Drive files.list ``q`` param
            as a ``fullText contains`` filter).
        folder_id : str, optional
            Restrict the search to a specific Drive folder ID.  Leave empty to
            search the entire service-account Drive.

        Returns
        -------
        str
            Concatenated document content, or DATA_UNAVAILABLE on failure.
        """
        return await self._call_with_retry(
            self._do_fetch_documents, query, folder_id=folder_id
        )

    async def fetch_document_by_id(self, file_id: str) -> str:
        """
        Download and return the text content of a specific Drive file by ID.

        Parameters
        ----------
        file_id : str
            The Google Drive file ID.

        Returns
        -------
        str
            File content as plain text, or DATA_UNAVAILABLE on failure.
        """
        return await self._call_with_retry(self._do_fetch_by_id, file_id)

    async def list_recent(self, max_files: int = 10) -> str:
        """
        List recently modified files in the service account's Drive.

        Parameters
        ----------
        max_files : int
            Maximum number of files to list (default 10).

        Returns
        -------
        str
            Formatted file listing, or DATA_UNAVAILABLE on failure.
        """
        return await self._call_with_retry(self._do_list, max_files=max_files)

    # ── Internal ───────────────────────────────────────────────────────────────

    async def _do_fetch_documents(self, query: str, folder_id: str = "") -> str:
        credentials = self._load_credentials()
        if isinstance(credentials, str):
            return credentials  # error string

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, _search_and_fetch_sync, credentials, query, folder_id
        )

    async def _do_fetch_by_id(self, file_id: str) -> str:
        credentials = self._load_credentials()
        if isinstance(credentials, str):
            return credentials  # error string

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _fetch_sync, credentials, file_id)

    async def _do_list(self, max_files: int = 10) -> str:
        credentials = self._load_credentials()
        if isinstance(credentials, str):
            return credentials  # error string

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _list_sync, credentials, max_files)

    def _load_credentials(self) -> Any:
        """
        Load and return service account credentials, or an error string.
        """
        creds_path = self._settings.google_drive_credentials
        if not creds_path:
            return "DRIVE_UNAVAILABLE: GOOGLE_DRIVE_CREDENTIALS not configured."

        if not Path(creds_path).exists():
            return f"DRIVE_UNAVAILABLE: Credentials file not found at {creds_path}."

        try:
            from google.oauth2 import service_account  # type: ignore[import]
        except ImportError:
            return "DRIVE_UNAVAILABLE: google-auth package not installed."

        try:
            return service_account.Credentials.from_service_account_file(
                creds_path, scopes=_DRIVE_SCOPES
            )
        except Exception as exc:
            return f"DRIVE_UNAVAILABLE: Failed to load credentials — {exc}"


# ── Synchronous helpers (run in executor) ─────────────────────────────────────

def _search_and_fetch_sync(credentials: Any, query: str, folder_id: str) -> str:
    """Search Drive for documents matching the query, then fetch their content."""
    try:
        from googleapiclient.discovery import build  # type: ignore[import]
    except ImportError:
        return "DRIVE_UNAVAILABLE: google-api-python-client not installed."

    service = build("drive", "v3", credentials=credentials)

    # Build the query string
    q_parts = [f"fullText contains '{query.replace(chr(39), chr(92) + chr(39))}'"]
    if folder_id:
        q_parts.append(f"'{folder_id}' in parents")
    q_parts.append("trashed = false")
    drive_query = " and ".join(q_parts)

    results = (
        service.files()
        .list(
            q=drive_query,
            pageSize=5,
            orderBy="relevance",
            fields="files(id,name,mimeType,modifiedTime)",
        )
        .execute()
    )
    files = results.get("files", [])
    if not files:
        return f"No Drive documents found for query: {query!r}"

    sections: list[str] = [f"Google Drive Documents — Query: {query!r}\n"]
    for f in files:
        file_id = f["id"]
        name = f.get("name", "Untitled")
        modified = (f.get("modifiedTime") or "")[:10]
        sections.append(f"--- Document: {name} (modified {modified}) ---")
        try:
            content = _fetch_sync(credentials, file_id)
        except Exception as exc:
            content = f"[Could not fetch content: {exc}]"
        sections.append(content[:_MAX_CONTENT_CHARS])
        sections.append("")  # blank line between documents

    return "\n".join(sections)


def _fetch_sync(credentials: Any, file_id: str) -> str:
    """Synchronous Drive file fetch by ID — run in executor."""
    try:
        from googleapiclient.discovery import build  # type: ignore[import]
        from googleapiclient.http import MediaIoBaseDownload  # type: ignore[import]
    except ImportError:
        return "DRIVE_UNAVAILABLE: google-api-python-client not installed."

    import io

    service = build("drive", "v3", credentials=credentials)

    # Get file metadata to determine MIME type
    meta = service.files().get(fileId=file_id, fields="name,mimeType").execute()
    mime_type = meta.get("mimeType", "")
    name = meta.get("name", file_id)

    if "google-apps.document" in mime_type:
        # Export Google Doc as plain text
        result = (
            service.files()
            .export(fileId=file_id, mimeType="text/plain")
            .execute()
        )
        content = result.decode("utf-8") if isinstance(result, bytes) else str(result)
    elif "google-apps.spreadsheet" in mime_type:
        # Export Google Sheet as CSV
        result = (
            service.files()
            .export(fileId=file_id, mimeType="text/csv")
            .execute()
        )
        content = result.decode("utf-8") if isinstance(result, bytes) else str(result)
    elif "google-apps.presentation" in mime_type:
        # Export Google Slides as plain text
        result = (
            service.files()
            .export(fileId=file_id, mimeType="text/plain")
            .execute()
        )
        content = result.decode("utf-8") if isinstance(result, bytes) else str(result)
    else:
        # Download as binary and decode
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        content = fh.getvalue().decode("utf-8", errors="replace")

    return content[:_MAX_CONTENT_CHARS]


def _list_sync(credentials: Any, max_files: int) -> str:
    """Synchronous Drive file listing — run in executor."""
    try:
        from googleapiclient.discovery import build  # type: ignore[import]
    except ImportError:
        return "DRIVE_UNAVAILABLE: google-api-python-client not installed."

    service = build("drive", "v3", credentials=credentials)
    results = (
        service.files()
        .list(
            pageSize=max_files,
            orderBy="modifiedTime desc",
            q="trashed = false",
            fields="files(id,name,mimeType,modifiedTime,size)",
        )
        .execute()
    )
    files = results.get("files", [])
    if not files:
        return "No files found in Drive."
    lines = [f"Recent Drive files ({len(files)}):"]
    for f in files:
        size_str = f"  {int(f.get('size', 0)) // 1024}KB" if f.get("size") else ""
        lines.append(
            f"  • [{f['id']}] {f['name']}"
            f" ({(f.get('modifiedTime') or '')[:10]})"
            f"{size_str}"
        )
    return "\n".join(lines)
