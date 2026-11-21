import os
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.services.ingestion as ingestion_module
from app.config import Settings
from app.db import Base
from app.models import Chunk, Document, IndexVersion, IngestionTask, KnowledgeBase
from app.services.bm25 import BM25Index
from app.services.ingestion import IngestionService

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_QDRANT_TESTS") != "1", reason="set RUN_QDRANT_TESTS=1 with Qdrant running"
)


class DeterministicEmbeddings:
    def __init__(self, _settings: Settings) -> None:
        pass

    async def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            value = sum(ord(character) for character in text)
            vector = [0.0] * 1024
            vector[value % 1024] = 1.0
            vector[(value * 7) % 1024] = 0.5
            vectors.append(vector)
        return vectors

    async def close(self) -> None:
        pass


async def test_a4_snapshot_publishes_consistent_indexes(tmp_path, monkeypatch) -> None:
    settings = Settings(
        data_dir=tmp_path / "data",
        database_url=f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
        qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"),
        llm_api_key="test-only",
        dashscope_api_key="test-only",
    )
    settings.ensure_directories()
    engine = create_engine(settings.sqlalchemy_url)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(ingestion_module, "SessionLocal", sessions)
    monkeypatch.setattr(ingestion_module, "EmbeddingClient", DeterministicEmbeddings)

    source = (
        Path(__file__).parents[2]
        / "docs/样例文件/01-第一次迭代/nist-ams-400-1-on-machine-measurement.pdf"
    )
    storage_key = f"{uuid.uuid4()}.pdf"
    destination = settings.data_dir / "documents" / storage_key
    destination.write_bytes(source.read_bytes())
    with sessions() as db:
        document = Document(
            name="nist-ams-400-1.pdf",
            content_sha256="e0fff763cdbc652ed87d02e65b15f1c6e099b40addd4b3e379225da499dcf165",
            size_bytes=source.stat().st_size,
            storage_key=storage_key,
        )
        db.add(document)
        db.flush()
        task = IngestionTask(document_id=document.id)
        db.add(task)
        db.commit()
        task_id = task.id
        document_id = document.id

    service = IngestionService(settings)
    collection = None
    try:
        await service.process(task_id)
        with sessions() as db:
            document = db.get(Document, document_id)
            task = db.get(IngestionTask, task_id)
            assert document.status == "ready", document.failure_message
            assert document.page_count == 69
            assert document.chunk_count > 69
            assert task.status == "succeeded"
            version = db.get(IndexVersion, document.index_version_id)
            assert version.status == "ready"
            collection = version.qdrant_collection
            kb = db.get(KnowledgeBase, version.knowledge_base_id)
            assert kb.active_index_version_id == version.id
            chunk_ids = set(
                db.scalars(select(Chunk.id).where(Chunk.index_version_id == version.id)).all()
            )
            assert chunk_ids == await service.store.chunk_ids(collection)
            bm25 = BM25Index.load(settings.data_dir / version.bm25_path)
            assert {chunk.id for chunk in bm25.chunks} == chunk_ids
            assert len(chunk_ids) == version.chunk_count
    finally:
        if collection:
            await service.store.delete(collection)
        await service.close()
