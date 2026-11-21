import asyncio
import json
import logging
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select

from app.config import Settings
from app.db import SessionLocal
from app.models import (
    Chunk,
    Document,
    IndexVersion,
    IndexVersionDocument,
    IngestionTask,
    KnowledgeBase,
    utcnow,
)
from app.services.bm25 import BM25Index
from app.services.chunking import chunk_pages
from app.services.domain import ChunkData
from app.services.embeddings import EmbeddingClient, ModelServiceError
from app.services.pdf import PDFParseError, parse_pdf
from app.services.vector_store import QdrantStore

logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(self, settings: Settings, store: QdrantStore | None = None) -> None:
        self.settings = settings
        self.store = store or QdrantStore(settings.qdrant_url)

    def recover_expired_tasks(self) -> None:
        now = datetime.now(UTC)
        with SessionLocal() as db:
            tasks = db.scalars(select(IngestionTask).where(IngestionTask.status == "running")).all()
            for task in tasks:
                lease = task.lease_expires_at
                if lease and lease.tzinfo is None:
                    lease = lease.replace(tzinfo=UTC)
                if lease is None or lease < now:
                    task.status = "queued"
                    task.stage = "recovering"
                    task.lease_expires_at = None
            db.commit()

    def claim_next(self) -> str | None:
        with SessionLocal() as db:
            task = db.scalar(
                select(IngestionTask)
                .where(IngestionTask.status == "queued")
                .order_by(IngestionTask.created_at)
                .limit(1)
            )
            if not task:
                return None
            task.status = "running"
            task.stage = "file_check"
            task.attempts += 1
            task.lease_expires_at = datetime.now(UTC) + timedelta(minutes=30)
            document = db.get(Document, task.document_id)
            document.status = "parsing"
            document.failure_stage = None
            document.failure_message = None
            db.commit()
            return task.id

    def _set_stage(self, task_id: str, stage: str, status: str | None = None) -> None:
        with SessionLocal() as db:
            task = db.get(IngestionTask, task_id)
            task.stage = stage
            task.checkpoint = {**(task.checkpoint or {}), "last_completed_stage": stage}
            if stage in {"embedding", "indexing", "publishing"}:
                db.get(Document, task.document_id).status = "indexing"
            if status:
                task.status = status
            db.commit()

    async def process(self, task_id: str) -> None:
        version_id = str(uuid.uuid4())
        collection = f"kb_default__iv_{version_id}"
        bm25_relative = Path("indexes") / "bm25" / version_id
        try:
            with SessionLocal() as db:
                task = db.get(IngestionTask, task_id)
                current = db.get(Document, task.document_id)
                kb = db.scalar(select(KnowledgeBase).where(KnowledgeBase.name == "default"))
                if not kb:
                    kb = KnowledgeBase(name="default")
                    db.add(kb)
                    db.flush()
                version = IndexVersion(
                    id=version_id,
                    knowledge_base_id=kb.id,
                    parser_version=self.settings.parser_version,
                    chunking_version=self.settings.chunking_version,
                    embedding_model=self.settings.embedding_model,
                    embedding_dimension=self.settings.embedding_dimensions,
                    qdrant_collection=collection,
                    bm25_path=bm25_relative.as_posix(),
                )
                task.index_version_id = version_id
                db.add(version)
                documents = db.scalars(
                    select(Document).where(Document.status.in_(["ready", "parsing", "indexing"]))
                ).all()
                document_infos = [
                    {
                        "id": document.id,
                        "name": document.name,
                        "sha256": document.content_sha256,
                        "storage_key": document.storage_key,
                    }
                    for document in documents
                ]
                if current.id not in {document["id"] for document in document_infos}:
                    document_infos.append(
                        {
                            "id": current.id,
                            "name": current.name,
                            "sha256": current.content_sha256,
                            "storage_key": current.storage_key,
                        }
                    )
                db.commit()

            self._set_stage(task_id, "parsing")
            all_chunks: list[ChunkData] = []
            pages_by_document: dict[str, list] = {}
            counts: dict[str, int] = {}
            for info in document_infos:
                path = Path(self.settings.data_dir) / "documents" / info["storage_key"]
                pages = await asyncio.to_thread(parse_pdf, path, self.settings.max_pdf_pages)
                pages_by_document[info["id"]] = pages
                chunks = chunk_pages(
                    pages,
                    content_sha256=info["sha256"],
                    document_id=info["id"],
                    document_name=info["name"],
                    version=self.settings.chunking_version,
                    target_chars=self.settings.chunk_target_chars,
                    overlap_chars=self.settings.chunk_overlap_chars,
                    min_chars=self.settings.chunk_min_chars,
                )
                counts[info["id"]] = len(chunks)
                all_chunks.extend(chunks)
                parsed_dir = Path(self.settings.data_dir) / "parsed" / version_id
                parsed_dir.mkdir(parents=True, exist_ok=True)
                (parsed_dir / f"{info['id']}.json").write_text(
                    json.dumps([page.__dict__ for page in pages], ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

            with SessionLocal() as db:
                for info in document_infos:
                    document_chunks = [
                        chunk for chunk in all_chunks if chunk.document_id == info["id"]
                    ]
                    db.add_all(
                        [
                            Chunk(
                                id=chunk.id,
                                index_version_id=version_id,
                                document_id=chunk.document_id,
                                ordinal=chunk.ordinal,
                                text=chunk.text,
                                page_start=chunk.page_start,
                                page_end=chunk.page_end,
                                section_path=chunk.section_path,
                                char_start=chunk.char_start,
                                char_end=chunk.char_end,
                                token_count=chunk.token_count,
                            )
                            for chunk in document_chunks
                        ]
                    )
                    db.add(
                        IndexVersionDocument(
                            index_version_id=version_id,
                            document_id=info["id"],
                            content_sha256=info["sha256"],
                            chunk_count=len(document_chunks),
                        )
                    )
                db.commit()

            self._set_stage(task_id, "embedding")
            embedder = EmbeddingClient(self.settings)
            try:
                vectors = await embedder.embed([chunk.text for chunk in all_chunks])
            finally:
                await embedder.close()

            self._set_stage(task_id, "indexing")
            await self.store.create_version(
                collection,
                version_id,
                all_chunks,
                vectors,
                self.settings.embedding_dimensions,
            )
            bm25 = BM25Index.build(all_chunks)
            await asyncio.to_thread(bm25.save, Path(self.settings.data_dir) / bm25_relative)
            vector_ids = await self.store.chunk_ids(collection)
            bm25_ids = {chunk.id for chunk in bm25.chunks}
            if vector_ids != bm25_ids or len(vector_ids) != len(all_chunks):
                raise RuntimeError("两路索引分块一致性检查失败")

            self._set_stage(task_id, "publishing")
            with SessionLocal() as db:
                version = db.get(IndexVersion, version_id)
                kb = db.get(KnowledgeBase, version.knowledge_base_id)
                previous_id = kb.active_index_version_id
                if previous_id and previous_id != version_id:
                    previous = db.get(IndexVersion, previous_id)
                    if previous:
                        previous.status = "retired"
                version.status = "ready"
                version.chunk_count = len(all_chunks)
                version.published_at = utcnow()
                kb.active_index_version_id = version_id
                for info in document_infos:
                    document = db.get(Document, info["id"])
                    document.status = "ready"
                    document.page_count = len(pages_by_document[info["id"]])
                    document.chunk_count = counts[info["id"]]
                    document.index_version_id = version_id
                    document.failure_stage = None
                    document.failure_message = None
                task = db.get(IngestionTask, task_id)
                task.status = "succeeded"
                task.stage = "published"
                task.lease_expires_at = None
                task.checkpoint = {
                    **(task.checkpoint or {}),
                    "chunk_count": len(all_chunks),
                    "index_version_id": version_id,
                }
                db.commit()
        except Exception as exc:
            await self._mark_failed(task_id, version_id, exc)

    async def _mark_failed(self, task_id: str, version_id: str, exc: Exception) -> None:
        if isinstance(exc, PDFParseError | ModelServiceError):
            message = str(exc)
            code = (
                "DOCUMENT_PARSE_FAILED" if isinstance(exc, PDFParseError) else "MODEL_UNAVAILABLE"
            )
        elif isinstance(exc, RuntimeError) and "一致性" in str(exc):
            message = str(exc)
            code = "INDEX_CONSISTENCY_FAILED"
        else:
            message = "文档处理失败，请检查文件和服务状态后重试"
            code = "INGESTION_FAILED"
        with SessionLocal() as db:
            task = db.get(IngestionTask, task_id)
            if task:
                task.status = "failed"
                task.error_code = code
                task.error_message = message
                task.lease_expires_at = None
                document = db.get(Document, task.document_id)
                if document:
                    document.status = "failed"
                    document.failure_stage = task.stage
                    document.failure_message = message
            version = db.get(IndexVersion, version_id)
            if version and version.status == "building":
                version.status = "failed"
            db.commit()
        logger.exception("Ingestion task %s failed: %s", task_id, code)

    async def close(self) -> None:
        await self.store.close()


async def worker_loop(once: bool = False) -> None:
    settings = Settings()
    settings.ensure_directories()
    service = IngestionService(settings)
    try:
        while True:
            settings = Settings()
            settings.ensure_directories()
            service.settings = settings
            service.recover_expired_tasks()
            task_id = await asyncio.to_thread(service.claim_next)
            if task_id:
                await service.process(task_id)
            elif once:
                return
            else:
                await asyncio.sleep(1)
    finally:
        await service.close()
