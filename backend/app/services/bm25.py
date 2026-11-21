import json
import pickle
import re
from pathlib import Path

import jieba
from rank_bm25 import BM25Okapi

from app.services.domain import ChunkData, SearchHit

_TERM_RE = re.compile(r"[a-z0-9]+(?:[._+/-][a-z0-9]+)*|[\u4e00-\u9fff]+")


def tokenize(text: str) -> list[str]:
    terms: list[str] = []
    for match in _TERM_RE.finditer(text.lower()):
        term = match.group()
        if "\u4e00" <= term[0] <= "\u9fff":
            terms.extend(part.strip() for part in jieba.lcut(term) if part.strip())
        else:
            terms.append(term)
    return terms


class BM25Index:
    def __init__(self, chunks: list[ChunkData], tokenized: list[list[str]]) -> None:
        self.chunks = chunks
        self.tokenized = tokenized
        self.engine = BM25Okapi(tokenized)

    @classmethod
    def build(cls, chunks: list[ChunkData]) -> "BM25Index":
        return cls(chunks, [tokenize(chunk.text) for chunk in chunks])

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        payload = {"format_version": 1, "chunks": self.chunks, "tokenized": self.tokenized}
        temporary = directory / "index.pkl.tmp"
        with temporary.open("wb") as handle:
            pickle.dump(payload, handle)
        temporary.replace(directory / "index.pkl")
        (directory / "manifest.json").write_text(
            json.dumps(
                {"format_version": 1, "chunk_count": len(self.chunks)},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, directory: Path) -> "BM25Index":
        with (directory / "index.pkl").open("rb") as handle:
            payload = pickle.load(handle)
        if payload.get("format_version") != 1:
            raise ValueError("BM25 索引格式不兼容")
        return cls(payload["chunks"], payload["tokenized"])

    def search(
        self, query: str, top_k: int, document_ids: list[str] | None = None
    ) -> list[SearchHit]:
        query_terms = tokenize(query)
        if not query_terms:
            return []
        scores = self.engine.get_scores(query_terms)
        allowed = set(document_ids) if document_ids else None
        ranked = sorted(
            (
                (index, float(score))
                for index, score in enumerate(scores)
                if score > 0 and (allowed is None or self.chunks[index].document_id in allowed)
            ),
            key=lambda item: (-item[1], self.chunks[item[0]].id),
        )[:top_k]
        hits: list[SearchHit] = []
        for rank, (index, score) in enumerate(ranked, start=1):
            chunk = self.chunks[index]
            hits.append(
                SearchHit(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    document_name=chunk.document_name,
                    text=chunk.text,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    section_path=chunk.section_path,
                    score=score,
                    rank=rank,
                    matched_terms=sorted(set(query_terms) & set(self.tokenized[index])),
                )
            )
        return hits
