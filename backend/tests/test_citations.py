import pytest

from app.services.citations import (
    CitationValidationError,
    citation_labels,
    citations_for_labels,
    validate_citation_labels,
)
from app.services.context import build_context
from app.services.domain import Candidate, SearchHit


def test_citation_whitelist_rejects_unknown_labels() -> None:
    assert citation_labels("结论[1]，另一结论[12]") == [1, 12]
    with pytest.raises(CitationValidationError):
        validate_citation_labels([1, 12], {1, 2})


def test_citation_snapshots_come_only_from_context() -> None:
    hit = SearchHit("chunk-1", "doc-1", "process.pdf", "original text", 4, 4, [], 0.8)
    items = build_context([Candidate(hit=hit, rerank_score=0.9)])
    citations = citations_for_labels(items, [1])
    assert citations[0]["excerpt"] == "original text"
    assert citations[0]["page_start"] == 4
