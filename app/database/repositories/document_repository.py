from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import DocumentStatus
from app.database.models.document import Document


class DocumentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: int, filename: str, file_size: int) -> Document:
        doc = Document(
            user_id=user_id,
            filename=filename,
            file_size=file_size,
            status=DocumentStatus.RECEIVED,
        )
        self.session.add(doc)
        await self.session.flush()
        return doc

    async def mark_status(self, document: Document, status: DocumentStatus) -> None:
        document.status = status
        if status == DocumentStatus.DELETED:
            import datetime as dt

            document.deleted_at = dt.datetime.now(dt.timezone.utc)
        await self.session.flush()

    async def get(self, document_id: int) -> Document | None:
        return await self.session.get(Document, document_id)
