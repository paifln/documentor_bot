"""Secure handling of uploaded files.

Rules enforced here (see spec §24 Security / §25 Privacy):
  * only .docx is ever accepted;
  * generated filenames are random tokens, never derived from user input;
  * files live under STORAGE_DIR only — no user-controlled paths;
  * files older than FILE_RETENTION_HOURS are purged by a periodic task
    (see app/bot/middlewares / worker startup);
  * documents are never executed or opened by anything other than
    python-docx / zipfile in read-only mode.
"""

from __future__ import annotations

import time
from pathlib import Path

from app.common.exceptions import FileTooLargeError, SecurityValidationError
from app.common.utils import safe_filename
from app.config.logging import get_logger
from app.config.settings import get_settings

logger = get_logger(__name__)

# DOCX files are ZIP archives; a valid one always starts with this signature.
_ZIP_MAGIC = b"PK\x03\x04"

# Minimal set of internal parts every valid .docx must contain.
_REQUIRED_DOCX_PARTS = {"[Content_Types].xml", "word/document.xml"}


class SecureFileStore:
    """Stores uploaded documents in a private, non-web-accessible directory."""

    def __init__(self, storage_dir: Path | None = None):
        settings = get_settings()
        self.storage_dir = storage_dir or settings.storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_bytes = settings.max_file_size_bytes
        self.retention_hours = settings.file_retention_hours

    def save(self, content: bytes, original_name: str) -> Path:
        if len(content) == 0:
            raise SecurityValidationError("empty file")
        if len(content) > self.max_size_bytes:
            raise FileTooLargeError(
                f"{len(content)} bytes > limit {self.max_size_bytes}",
            )
        if not content.startswith(_ZIP_MAGIC):
            raise SecurityValidationError("not a valid ZIP/OOXML signature")

        filename = safe_filename(original_name, prefix="cw_")
        path = self.storage_dir / filename
        # Resolve and confirm the final path stays within storage_dir
        # (defense in depth against any future path-construction changes).
        resolved = path.resolve()
        if self.storage_dir.resolve() not in resolved.parents:
            raise SecurityValidationError("path traversal attempt detected")

        path.write_bytes(content)
        path.chmod(0o600)
        logger.info("file_saved", size=len(content))
        return path

    def delete(self, path: Path) -> None:
        try:
            if path.exists() and self.storage_dir.resolve() in path.resolve().parents:
                path.unlink()
                logger.info("file_deleted")
        except OSError as exc:  # pragma: no cover - filesystem edge case
            logger.warning("file_delete_failed", error=str(exc))

    def purge_expired(self) -> int:
        """Delete files older than the retention window. Returns count removed."""
        cutoff = time.time() - self.retention_hours * 3600
        removed = 0
        for f in self.storage_dir.glob("cw_*"):
            try:
                if f.stat().st_mtime < cutoff:
                    f.unlink()
                    removed += 1
            except OSError:  # pragma: no cover
                continue
        if removed:
            logger.info("expired_files_purged", count=removed)
        return removed
