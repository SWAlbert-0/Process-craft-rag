from app.services.context import build_context, format_context
from app.services.domain import Candidate, SearchHit


def candidate(chunk_id: str, text: str, score: float = 0.9) -> Candidate:
    return Candidate(
        hit=SearchHit(
            chunk_id=chunk_id,
            document_id="doc-1",
            document_name="process.pdf",
            text=text,
            page_start=3,
            page_end=3,
            section_path=["Measurement"],
            score=score,
        ),
        rerank_score=score,
    )


def test_context_budget_deduplication_and_labels() -> None:
    items = build_context(
        [
            candidate("a", "spindle calibration uses a reference artifact"),
            candidate("duplicate", "spindle calibration uses a reference artifact"),
            candidate("b", "record the measurement uncertainty"),
            candidate("low", "unrelated", score=0.1),
        ],
        token_budget=60,
        min_rerank_score=0.2,
    )
    assert [item.candidate.hit.chunk_id for item in items] == ["a", "b"]
    assert [item.label for item in items] == [1, 2]
    formatted = format_context(items)
    assert "PDF 物理页码：3" in formatted
    assert "<不可信原文数据>" in formatted


def test_context_never_returns_overbudget_first_item() -> None:
    assert build_context([candidate("large", "word " * 200)], token_budget=10) == []
