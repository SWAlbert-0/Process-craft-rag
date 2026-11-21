import hashlib
import shutil
import uuid
from datetime import UTC
from pathlib import PurePath

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.errors import AppError
from app.models import Chunk, Document, IndexVersion, IngestionTask
from app.services.vector_store import QdrantStore

router = APIRouter(prefix="/documents", tags=["documents"])
task_router = APIRouter(prefix="/ingestion-tasks", tags=["documents"])


def iso(value) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()


def document_dict(document: Document) -> dict:
    return {
        "id": document.id,
        "name": document.name,
        "content_sha256": document.content_sha256,
        "size_bytes": document.size_bytes,
        "page_count": document.page_count,
        "chunk_count": document.chunk_count,
        "status": document.status,
        "failure_stage": document.failure_stage,
        "failure_message": document.failure_message,
        "index_version_id": document.index_version_id,
        "created_at": iso(document.created_at),
        "updated_at": iso(document.updated_at),
    }


@router.post("")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    original_name = PurePath((file.filename or "document.pdf").replace("\\", "/")).name
    if not original_name.lower().endswith(".pdf"):
        raise AppError(422, "VALIDATION_ERROR", "仅支持 PDF 文件")

    maximum = settings.max_upload_mb * 1024 * 1024
    temporary = settings.data_dir / "tmp" / f"{uuid.uuid4()}.upload"
    digest = hashlib.sha256()
    size = 0
    header = b""
    try:
        with temporary.open("wb") as handle:
            while content := await file.read(1024 * 1024):
                size += len(content)
                if size > maximum:
                    raise AppError(
                        413, "VALIDATION_ERROR", f"文件超过 {settings.max_upload_mb} MB 上限"
                    )
                if not header:
                    header = content[:5]
                digest.update(content)
                handle.write(content)
        if size == 0 or header != b"%PDF-":
            raise AppError(422, "VALIDATION_ERROR", "文件不是有效的 PDF")

        content_hash = digest.hexdigest()
        existing = db.scalar(select(Document).where(Document.content_sha256 == content_hash))
        if existing:
            raise AppError(
                409,
                "DUPLICATE_DOCUMENT",
                "相同内容的文档已存在",
                {"document_id": existing.id},
            )
        storage_key = f"{uuid.uuid4()}.pdf"
        destination = settings.data_dir / "documents" / storage_key
        temporary.replace(destination)
        document = Document(
            name=original_name,
            content_sha256=content_hash,
            size_bytes=size,
            storage_key=storage_key,
        )
        db.add(document)
        db.flush()
        task = IngestionTask(document_id=document.id)
        db.add(task)
        db.commit()
        return JSONResponse(
            status_code=202,
            content={"document": document_dict(document), "task_id": task.id},
        )
    finally:
        await file.close()
        if temporary.exists():
            temporary.unlink()


@router.get("")
def list_documents(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = None,
    keyword: str | None = Query(default=None, max_length=100),
    db: Session = Depends(get_db),
) -> dict:
    filters = []
    if status:
        filters.append(Document.status == status)
    if keyword:
        filters.append(Document.name.contains(keyword))
    total = db.scalar(select(func.count(Document.id)).where(*filters)) or 0
    documents = db.scalars(
        select(Document)
        .where(*filters)
        .order_by(Document.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [document_dict(document) for document in documents],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.get("/{document_id}")
def get_document(document_id: str, db: Session = Depends(get_db)) -> dict:
    document = db.get(Document, document_id)
    if not document:
        raise AppError(404, "NOT_FOUND", "文档不存在")
    task = db.scalar(
        select(IngestionTask)
        .where(IngestionTask.document_id == document.id)
        .order_by(IngestionTask.created_at.desc())
    )
    return {
        **document_dict(document),
        "task_id": task.id if task else None,
        "stage": task.stage if task else None,
    }


@router.post("/{document_id}/retry")
def retry_document(
    document_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    document = db.get(Document, document_id)
    if not document:
        raise AppError(404, "NOT_FOUND", "文档不存在")
    if document.status != "failed":
        raise AppError(409, "DOCUMENT_NOT_READY", "只有处理失败的文档可以重试")
    if not (settings.data_dir / "documents" / document.storage_key).is_file():
        raise AppError(409, "DOCUMENT_NOT_READY", "原始文件不可用，无法重试")
    document.status = "pending"
    document.failure_stage = None
    document.failure_message = None
    task = IngestionTask(document_id=document.id)
    db.add(task)
    db.commit()
    return JSONResponse(
        status_code=202,
        content={"document": document_dict(document), "task_id": task.id},
    )


@router.delete("/{document_id}", status_code=204)
async def delete_failed_document(
    document_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    document = db.get(Document, document_id)
    if not document:
        raise AppError(404, "NOT_FOUND", "文档不存在")
    if document.status != "failed":
        raise AppError(409, "DOCUMENT_NOT_READY", "当前仅允许直接删除失败记录")
    if document.index_version_id:
        raise AppError(409, "DOCUMENT_NOT_READY", "文档仍关联已发布快照，不能直接删除")

    versions = db.scalars(
        select(IndexVersion)
        .join(IngestionTask, IngestionTask.index_version_id == IndexVersion.id)
        .where(IngestionTask.document_id == document.id, IndexVersion.status == "failed")
    ).all()
    document.status = "deleting"
    db.commit()
    store = QdrantStore(settings.qdrant_url)
    try:
        for version in versions:
            await store.delete(version.qdrant_collection)
    except Exception as exc:
        document.status = "failed"
        db.commit()
        raise AppError(503, "RETRIEVAL_FAILED", "暂存索引清理失败，请稍后重试") from exc
    finally:
        await store.close()

    db.execute(delete(IngestionTask).where(IngestionTask.document_id == document.id))
    for version in versions:
        db.delete(version)
    db.delete(document)
    db.commit()

    source = settings.data_dir / "documents" / document.storage_key
    if source.exists():
        source.unlink()
    for version in versions:
        shutil.rmtree(settings.data_dir / "parsed" / version.id, ignore_errors=True)
        shutil.rmtree(settings.data_dir / version.bm25_path, ignore_errors=True)
    return Response(status_code=204)


@router.get("/{document_id}/chunks")
def get_chunks(
    document_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    document = db.get(Document, document_id)
    if not document:
        raise AppError(404, "NOT_FOUND", "文档不存在")
    if not document.index_version_id:
        return {"items": [], "page": page, "page_size": page_size, "total": 0}
    filters = [
        Chunk.document_id == document_id,
        Chunk.index_version_id == document.index_version_id,
    ]
    total = db.scalar(select(func.count(Chunk.id)).where(*filters)) or 0
    chunks = db.scalars(
        select(Chunk)
        .where(*filters)
        .order_by(Chunk.ordinal)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [
            {
                "id": chunk.id,
                "ordinal": chunk.ordinal,
                "text": chunk.text,
                "page_start": chunk.page_start,
                "page_end": chunk.page_end,
                "section_path": chunk.section_path,
                "token_count": chunk.token_count,
            }
            for chunk in chunks
        ],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.get("/{document_id}/content")
def get_content(
    document_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    document = db.get(Document, document_id)
    if not document:
        raise AppError(404, "NOT_FOUND", "文档不存在")
    path = settings.data_dir / "documents" / document.storage_key
    if not path.is_file():
        raise AppError(404, "NOT_FOUND", "原始文件不可用")
    return FileResponse(path, media_type="application/pdf", filename=document.name)


@task_router.get("/{task_id}")
def get_task(task_id: str, db: Session = Depends(get_db)) -> dict:
    task = db.get(IngestionTask, task_id)
    if not task:
        raise AppError(404, "NOT_FOUND", "任务不存在")
    return {
        "id": task.id,
        "document_id": task.document_id,
        "index_version_id": task.index_version_id,
        "status": task.status,
        "stage": task.stage,
        "attempts": task.attempts,
        "error_code": task.error_code,
        "error_message": task.error_message,
        "created_at": iso(task.created_at),
        "updated_at": iso(task.updated_at),
    }
