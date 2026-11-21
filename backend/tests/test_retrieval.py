import pytest

from app.services.domain import SearchHit
from app.services.retrieval import reciprocal_rank_fusion


def hit(chunk_id: str, score: float, rank: int) -> SearchHit:
    return SearchHit(
        chunk_id=chunk_id,
        document_id="doc-1",
        document_name="process.pdf",
        text=chunk_id,
        page_start=1,
        page_end=1,
        section_path=[],
        score=score,
        rank=rank,
    )


def test_rrf_uses_both_routes_and_deduplicates() -> None:
    dense = [hit("a", 0.9, 1), hit("b", 0.8, 2)]
    sparse = [hit("b", 12.0, 1), hit("c", 10.0, 2)]
    fused = reciprocal_rank_fusion(dense, sparse, k=60, limit=10)
    assert [candidate.hit.chunk_id for candidate in fused] == ["b", "a", "c"]
    assert fused[0].dense_rank == 2
    assert fused[0].sparse_rank == 1
    assert fused[0].rrf_score == pytest.approx(1 / 62 + 1 / 61)
    assert fused[1].rrf_score == pytest.approx(1 / 61)


def test_rrf_rejects_invalid_constant() -> None:
    with pytest.raises(ValueError):
        reciprocal_rank_fusion([], [], k=0)
