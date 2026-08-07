"""Document translation job persistence and database helpers."""

from __future__ import annotations

import time
from typing import Any

from open_webui.internal.db import Base, JSONField, async_engine, get_async_db_context
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import BigInteger, Boolean, Column, String, Text, asc, delete, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession


class DocumentTranslationJob(Base):
    __tablename__ = 'document_translation_job'

    id = Column(String, primary_key=True, unique=True)
    user_id = Column(String, index=True)

    source_file_id = Column(String, index=True)
    source_filename = Column(Text)
    source_mime_type = Column(String, nullable=True)
    source_preview = Column(Text, nullable=True)

    target_language = Column(String, index=True)
    source_language = Column(String, nullable=True)
    model = Column(String, nullable=True)
    force_ocr = Column(Boolean, default=False)
    generate_output_file = Column(Boolean, default=True)

    status = Column(String, index=True)
    progress = Column(JSONField, nullable=True)
    translation_text = Column(Text, nullable=True)
    visual_qa = Column(JSONField, nullable=True)

    output_file_id = Column(String, nullable=True, index=True)
    output_file_name = Column(Text, nullable=True)

    error = Column(Text, nullable=True)
    created_at = Column(BigInteger, index=True)
    updated_at = Column(BigInteger, index=True)
    completed_at = Column(BigInteger, nullable=True, index=True)


class DocumentTranslationJobModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str

    source_file_id: str
    source_filename: str
    source_mime_type: str | None = None
    source_preview: str | None = None

    target_language: str
    source_language: str | None = None
    model: str | None = None
    force_ocr: bool = False
    generate_output_file: bool = True

    status: str
    progress: list[str] = Field(default_factory=list)
    translation_text: str | None = None
    visual_qa: dict[str, Any] | None = None

    output_file_id: str | None = None
    output_file_name: str | None = None

    error: str | None = None
    created_at: int
    updated_at: int
    completed_at: int | None = None


class DocumentTranslationJobsTable:
    async def ensure_table_exists(self) -> None:
        async with async_engine.begin() as conn:
            def _ensure_schema(sync_conn):
                DocumentTranslationJob.__table__.create(sync_conn, checkfirst=True)
                if sync_conn.dialect.name != 'sqlite':
                    return

                existing_columns = {
                    row[1]
                    for row in sync_conn.exec_driver_sql('PRAGMA table_info(document_translation_job)').fetchall()
                }
                if 'source_preview' not in existing_columns:
                    sync_conn.exec_driver_sql(
                        'ALTER TABLE document_translation_job ADD COLUMN source_preview TEXT'
                    )
                if 'visual_qa' not in existing_columns:
                    sync_conn.exec_driver_sql(
                        'ALTER TABLE document_translation_job ADD COLUMN visual_qa JSON'
                    )

            await conn.run_sync(_ensure_schema)

    async def create_job(
        self,
        form_data: dict[str, Any],
        db: AsyncSession | None = None,
    ) -> DocumentTranslationJobModel | None:
        async with get_async_db_context(db) as db:
            now = int(time.time())
            job = DocumentTranslationJob(
                **{
                    'id': form_data['id'],
                    'user_id': form_data['user_id'],
                    'source_file_id': form_data['source_file_id'],
                    'source_filename': form_data['source_filename'],
                    'source_mime_type': form_data.get('source_mime_type'),
                    'source_preview': form_data.get('source_preview'),
                    'target_language': form_data['target_language'],
                    'source_language': form_data.get('source_language'),
                    'model': form_data.get('model'),
                    'force_ocr': bool(form_data.get('force_ocr', False)),
                    'generate_output_file': bool(form_data.get('generate_output_file', True)),
                    'status': form_data.get('status', 'queued'),
                    'progress': form_data.get('progress') or [],
                    'translation_text': form_data.get('translation_text'),
                    'visual_qa': form_data.get('visual_qa'),
                    'output_file_id': form_data.get('output_file_id'),
                    'output_file_name': form_data.get('output_file_name'),
                    'error': form_data.get('error'),
                    'created_at': form_data.get('created_at', now),
                    'updated_at': form_data.get('updated_at', now),
                    'completed_at': form_data.get('completed_at'),
                }
            )

            db.add(job)
            await db.commit()
            await db.refresh(job)
            return DocumentTranslationJobModel.model_validate(job)

    async def update_job_by_id(
        self,
        id: str,
        updates: dict[str, Any],
        db: AsyncSession | None = None,
    ) -> DocumentTranslationJobModel | None:
        async with get_async_db_context(db) as db:
            payload = dict(updates)
            payload['updated_at'] = int(time.time())
            await db.execute(update(DocumentTranslationJob).where(DocumentTranslationJob.id == id).values(**payload))
            await db.commit()
            return await self.get_job_by_id(id=id, db=db)

    async def get_job_by_id(
        self,
        id: str,
        db: AsyncSession | None = None,
    ) -> DocumentTranslationJobModel | None:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(DocumentTranslationJob).where(DocumentTranslationJob.id == id))
            job = result.scalars().first()
            if not job:
                return None
            return DocumentTranslationJobModel.model_validate(job)

    async def get_jobs_by_user_id(
        self,
        user_id: str | None,
        skip: int = 0,
        limit: int = 50,
        db: AsyncSession | None = None,
    ) -> list[DocumentTranslationJobModel]:
        async with get_async_db_context(db) as db:
            stmt = select(DocumentTranslationJob).order_by(desc(DocumentTranslationJob.updated_at))
            if user_id is not None:
                stmt = stmt.where(DocumentTranslationJob.user_id == user_id)
            stmt = stmt.offset(skip).limit(limit)
            result = await db.execute(stmt)
            return [DocumentTranslationJobModel.model_validate(job) for job in result.scalars().all()]

    async def get_next_queued_job_by_user_id(
        self,
        user_id: str,
        db: AsyncSession | None = None,
    ) -> DocumentTranslationJobModel | None:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(DocumentTranslationJob)
                .where(DocumentTranslationJob.user_id == user_id)
                .where(DocumentTranslationJob.status == 'queued')
                .order_by(asc(DocumentTranslationJob.created_at))
                .limit(1)
            )
            job = result.scalars().first()
            if not job:
                return None
            return DocumentTranslationJobModel.model_validate(job)

    async def has_active_job_by_user_id(
        self,
        user_id: str,
        db: AsyncSession | None = None,
    ) -> bool:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(DocumentTranslationJob.id)
                .where(DocumentTranslationJob.user_id == user_id)
                .where(DocumentTranslationJob.status == 'running')
                .limit(1)
            )
            return result.scalars().first() is not None

    async def delete_job_by_id(
        self,
        id: str,
        db: AsyncSession | None = None,
    ) -> bool:
        async with get_async_db_context(db) as db:
            result = await db.execute(delete(DocumentTranslationJob).where(DocumentTranslationJob.id == id))
            await db.commit()
            return result.rowcount > 0


DocumentTranslationJobs = DocumentTranslationJobsTable()
