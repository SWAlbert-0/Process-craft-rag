import asyncio
import time
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Document, IndexVersion, KnowledgeBase
from app.services.bm25 import BM25Index
from app.services.context import build_context
from app.services.domain import Candidate, ContextItem
from app.services.embeddings import EmbeddingClient
from app.services.generation import generate_answer
from app.services.llm import LLMClient
from app.services.rerank import RerankClient
from app.services.retrieval import reciprocal_rank_fusion
from app.services.vector_store import QdrantStore


class EmptyKnowledgeBaseError(RuntimeError):
    pass


class DocumentNotReadyError(RuntimeError):
    pass


@dataclass
class RAGResult:
    content: str
    structured_content: dict | None
    citations: list[dict]
    insufficient_evidence: bool
    diagnostics: dict
    run_config: dict
    usage: dict


class RAGService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def active_version(self, db: Session) -> IndexVersion:
        kb = db.scalar(select(KnowledgeBase).where(KnowledgeBase.name == "default"))
        if not kb or not kb.active_index_version_id:
            raise EmptyKnowledgeBaseError("知识库为空，请先导入文本型 PDF")
        version = db.get(IndexVersion, kb.active_index_version_id)
        if not version or version.status != "ready":
            raise EmptyKnowledgeBaseError("当前没有可用的知识库快照")
        return version

    def validate_document_filter(
        self, db: Session, version: IndexVersion, document_ids: list[str] | None
    ) -> list[str] | None:
        if document_ids is None:
            return None
        if not document_ids:
            raise DocumentNotReadyError("检索范围不能为空")
        documents = db.scalars(select(Document).where(Document.id.in_(document_ids))).all()
        if len(documents) != len(set(document_ids)) or any(
            document.status != "ready" or document.index_version_id != version.id
            for document in documents
        ):
            raise DocumentNotReadyError("检索范围包含不存在或尚未就绪的文档")
        return list(set(document_ids))

    async def _retrieve(
        self, question: str, version: IndexVersion, document_ids: list[str] | None
    ) -> tuple[list[ContextItem], dict]:
        settings = self.settings
        embedder = EmbeddingClient(settings)
        reranker = RerankClient(settings)
        store = QdrantStore(settings.qdrant_url)
        started = time.perf_counter()
        sparse_task: asyncio.Task | None = None
        try:
            bm25_path = Path(settings.data_dir) / version.bm25_path
            bm25 = await asyncio.to_thread(BM25Index.load, bm25_path)
            sparse_task = asyncio.create_task(
                asyncio.to_thread(bm25.search, question, settings.sparse_top_k, document_ids)
            )
            vectors = await embedder.embed([question])
            dense = await store.search(
                version.qdrant_collection, vectors[0], settings.dense_top_k, document_ids
            )
            sparse = await sparse_task
            fused = reciprocal_rank_fusion(
                dense, sparse, k=settings.rrf_k, limit=settings.fusion_top_n
            )
            reranked: list[Candidate] = await reranker.rerank(
                question, fused, settings.rerank_top_n
            )
            items = build_context(
                reranked,
                token_budget=settings.context_token_budget,
                min_rerank_score=settings.rerank_min_score,
            )
            diagnostics = {
                "index_version_id": version.id,
                "dense": [hit.summary() for hit in dense],
                "sparse": [hit.summary() for hit in sparse],
                "fusion": [candidate.summary() for candidate in fused],
                "rerank": [candidate.summary() for candidate in reranked],
                "context_labels": [item.label for item in items],
                "retrieval_ms": round((time.perf_counter() - started) * 1000, 2),
            }
            return items, diagnostics
        finally:
            if sparse_task and not sparse_task.done():
                sparse_task.cancel()
            await embedder.close()
            await reranker.close()
            await store.close()

    async def answer(
        self,
        db: Session,
        question: str,
        mode: str,
        document_ids: list[str] | None = None,
    ) -> RAGResult:
        version = self.active_version(db)
        document_ids = self.validate_document_filter(db, version, document_ids)
        items, diagnostics = await self._retrieve(question, version, document_ids)
        llm = LLMClient(self.settings)
        started = time.perf_counter()
        try:
            content, structured, citations, insufficient, usage = await generate_answer(
                llm, question, mode, items
            )
        finally:
            await llm.close()
        diagnostics["generation_ms"] = round((time.perf_counter() - started) * 1000, 2)
        diagnostics["insufficient_evidence"] = insufficient
        run_config = {
            "index_version_id": version.id,
            "llm_model": self.settings.llm_model,
            "embedding_model": self.settings.embedding_model,
            "rerank_model": self.settings.rerank_model,
            "dense_top_k": self.settings.dense_top_k,
            "sparse_top_k": self.settings.sparse_top_k,
            "rrf_k": self.settings.rrf_k,
            "fusion_top_n": self.settings.fusion_top_n,
            "rerank_top_n": self.settings.rerank_top_n,
            "context_token_budget": self.settings.context_token_budget,
            "rerank_min_score": self.settings.rerank_min_score,
        }
        return RAGResult(
            content, structured, citations, insufficient, diagnostics, run_config, usage
        )
