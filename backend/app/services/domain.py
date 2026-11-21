from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PageText:
    page: int
    raw_text: str
    normalized_text: str


@dataclass(frozen=True)
class ChunkData:
    id: str
    document_id: str
    document_name: str
    ordinal: int
    text: str
    page_start: int
    page_end: int
    section_path: list[str] = field(default_factory=list)
    char_start: int | None = None
    char_end: int | None = None
    token_count: int = 0

    def payload(self, index_version_id: str) -> dict[str, Any]:
        return {
            "chunk_id": self.id,
            "document_id": self.document_id,
            "document_name": self.document_name,
            "index_version_id": index_version_id,
            "ordinal": self.ordinal,
            "text": self.text,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "section_path": self.section_path,
            "token_count": self.token_count,
        }


@dataclass(frozen=True)
class SearchHit:
    chunk_id: str
    document_id: str
    document_name: str
    text: str
    page_start: int
    page_end: int
    section_path: list[str]
    score: float
    rank: int = 0
    matched_terms: list[str] = field(default_factory=list)

    @classmethod
    def from_payload(cls, payload: dict[str, Any], score: float, rank: int = 0) -> "SearchHit":
        return cls(
            chunk_id=payload["chunk_id"],
            document_id=payload["document_id"],
            document_name=payload["document_name"],
            text=payload["text"],
            page_start=payload["page_start"],
            page_end=payload["page_end"],
            section_path=payload.get("section_path", []),
            score=float(score),
            rank=rank,
        )

    def summary(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "document_name": self.document_name,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "score": round(self.score, 8),
            "rank": self.rank,
            "matched_terms": self.matched_terms,
        }


@dataclass
class Candidate:
    hit: SearchHit
    dense_rank: int | None = None
    sparse_rank: int | None = None
    dense_score: float | None = None
    sparse_score: float | None = None
    rrf_score: float = 0.0
    fusion_rank: int = 0
    rerank_score: float | None = None
    rerank_rank: int | None = None

    def summary(self) -> dict[str, Any]:
        data = self.hit.summary()
        data.update(
            {
                "dense_rank": self.dense_rank,
                "sparse_rank": self.sparse_rank,
                "dense_score": self.dense_score,
                "sparse_score": self.sparse_score,
                "rrf_score": round(self.rrf_score, 8),
                "fusion_rank": self.fusion_rank,
                "rerank_score": self.rerank_score,
                "rerank_rank": self.rerank_rank,
            }
        )
        data.pop("score", None)
        data.pop("rank", None)
        return data


@dataclass(frozen=True)
class ContextItem:
    label: int
    candidate: Candidate

    @property
    def citation(self) -> dict[str, Any]:
        hit = self.candidate.hit
        return {
            "label": self.label,
            "chunk_id": hit.chunk_id,
            "document_id": hit.document_id,
            "document_name": hit.document_name,
            "page_start": hit.page_start,
            "page_end": hit.page_end,
            "excerpt": hit.text,
            "rerank_score": self.candidate.rerank_score,
            "source_available": True,
        }
