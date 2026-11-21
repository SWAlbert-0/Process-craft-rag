import httpx
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.api.documents as documents_api
from app.config import Settings, get_settings
from app.db import Base, get_db
from app.main import app as fastapi_app
from app.models import Document, IndexVersion, IngestionTask, KnowledgeBase


class FakeQdrantStore:
    deleted: list[str] = []

    def __init__(self, _url: str) -> None:
        pass

    async def delete(self, collection: str) -> None:
        self.deleted.append(collection)

    async def close(self) -> None:
        pass


@pytest_asyncio.fixture
async def document_client(tmp_path, monkeypatch):
    settings = Settings(data_dir=tmp_path / "data", qdrant_url="http://qdrant.test")
    settings.ensure_directories()
    engine = create_engine(settings.sqlalchemy_url)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)

    def override_db():
        with sessions() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_db
    fastapi_app.dependency_overrides[get_settings] = lambda: settings
    monkeypatch.setattr(documents_api, "QdrantStore", FakeQdrantStore)
    FakeQdrantStore.deleted = []
    with sessions() as db:
        kb = KnowledgeBase(name="default")
        db.add(kb)
        db.flush()
        version = IndexVersion(
            id="failed-version",
            knowledge_base_id=kb.id,
            status="failed",
            parser_version="test",
            chunking_version="test",
            embedding_model="test",
            embedding_dimension=1024,
            qdrant_collection="kb_default__iv_failed-version",
            bm25_path="indexes/bm25/failed-version",
        )
        db.add(version)
        document = Document(
            id="failed-document",
            name="broken.pdf",
            content_sha256="a" * 64,
            size_bytes=5,
            status="failed",
            storage_key="failed.pdf",
            failure_stage="parsing",
            failure_message="parse failed",
        )
        db.add(document)
        db.add(
            IngestionTask(
                id="failed-task",
                document_id=document.id,
                index_version_id=version.id,
                status="failed",
                stage="parsing",
                error_message="parse failed",
            )
        )
        db.commit()
    (settings.data_dir / "documents" / "failed.pdf").write_bytes(b"%PDF-")
    client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=fastapi_app), base_url="http://test"
    )
    yield client, sessions, settings
    await client.aclose()
    fastapi_app.dependency_overrides.clear()


async def test_failed_document_can_retry(document_client) -> None:
    client, sessions, _settings = document_client
    response = await client.post("/api/v1/documents/failed-document/retry")
    assert response.status_code == 202
    assert response.json()["document"]["status"] == "pending"
    with sessions() as db:
        document = db.get(Document, "failed-document")
        assert document.status == "pending"
        assert document.failure_message is None
        assert db.get(IngestionTask, response.json()["task_id"]).status == "queued"


async def test_failed_document_can_be_deleted_with_staging_version(document_client) -> None:
    client, sessions, settings = document_client
    response = await client.delete("/api/v1/documents/failed-document")
    assert response.status_code == 204
    with sessions() as db:
        assert db.get(Document, "failed-document") is None
        assert db.get(IngestionTask, "failed-task") is None
        assert db.get(IndexVersion, "failed-version") is None
    assert not (settings.data_dir / "documents" / "failed.pdf").exists()
    assert FakeQdrantStore.deleted == ["kb_default__iv_failed-version"]


async def test_ready_document_cannot_use_failed_record_delete(document_client) -> None:
    client, sessions, _settings = document_client
    with sessions() as db:
        document = db.get(Document, "failed-document")
        document.status = "ready"
        db.commit()
    response = await client.delete("/api/v1/documents/failed-document")
    assert response.status_code == 409
