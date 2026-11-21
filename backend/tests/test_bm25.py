from app.services.bm25 import BM25Index, tokenize
from app.services.domain import ChunkData


def make_chunk(chunk_id: str, text: str, document_id: str = "doc-1") -> ChunkData:
    return ChunkData(
        id=chunk_id,
        document_id=document_id,
        document_name="process.pdf",
        ordinal=0,
        text=text,
        page_start=1,
        page_end=1,
        token_count=10,
    )


def test_tokenization_preserves_model_and_unit_terms() -> None:
    terms = tokenize("CNC-450 主轴 1200 rpm，公差 ±0.05 mm")
    assert {"cnc-450", "主轴", "1200", "rpm", "0.05", "mm"} <= set(terms)


def test_bm25_persists_and_filters(tmp_path) -> None:
    chunks = [
        make_chunk("chunk-a", "CNC-450 spindle runs at 1200 rpm"),
        make_chunk("chunk-b", "量具校准和测量不确定度"),
        make_chunk("chunk-c", "other CNC-450 maintenance", document_id="doc-2"),
    ]
    index = BM25Index.build(chunks)
    index.save(tmp_path / "bm25")
    loaded = BM25Index.load(tmp_path / "bm25")
    hits = loaded.search("CNC-450", top_k=10)
    assert {hit.chunk_id for hit in hits} == {"chunk-a", "chunk-c"}
    assert all("cnc-450" in hit.matched_terms for hit in hits)
    filtered = loaded.search("CNC-450", top_k=10, document_ids=["doc-2"])
    assert [hit.chunk_id for hit in filtered] == ["chunk-c"]
