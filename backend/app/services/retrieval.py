from app.services.domain import Candidate, SearchHit


def reciprocal_rank_fusion(
    dense: list[SearchHit], sparse: list[SearchHit], k: int = 60, limit: int = 30
) -> list[Candidate]:
    if k <= 0:
        raise ValueError("RRF k 必须大于 0")
    candidates: dict[str, Candidate] = {}
    for source, hits in (("dense", dense), ("sparse", sparse)):
        for fallback_rank, hit in enumerate(hits, start=1):
            rank = hit.rank or fallback_rank
            candidate = candidates.setdefault(hit.chunk_id, Candidate(hit=hit))
            candidate.rrf_score += 1.0 / (k + rank)
            if source == "dense":
                candidate.dense_rank = rank
                candidate.dense_score = hit.score
            else:
                candidate.sparse_rank = rank
                candidate.sparse_score = hit.score

    ordered = sorted(
        candidates.values(),
        key=lambda candidate: (
            -candidate.rrf_score,
            candidate.dense_rank or 10**9,
            candidate.hit.chunk_id,
        ),
    )
    for rank, candidate in enumerate(ordered, start=1):
        candidate.fusion_rank = rank
    return ordered[:limit]
