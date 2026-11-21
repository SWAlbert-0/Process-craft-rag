from app.services.chunking import chunk_pages, estimate_tokens, stable_chunk_id
from app.services.domain import PageText


def pages() -> list[PageText]:
    text = "2.1 Spindle calibration\n\n" + "Check spindle alignment before machining. " * 12
    return [
        PageText(page=1, raw_text=text, normalized_text=text),
        PageText(
            page=2,
            raw_text="公差 ±0.05 mm，设备 CNC-450。",
            normalized_text="公差 ±0.05 mm，设备 CNC-450。",
        ),
        PageText(page=3, raw_text="", normalized_text=""),
    ]


def test_chunking_is_deterministic_and_tracks_pages() -> None:
    kwargs = {
        "content_sha256": "a" * 64,
        "document_id": "doc-1",
        "document_name": "process.pdf",
        "target_chars": 180,
        "overlap_chars": 20,
        "min_chars": 10,
    }
    first = chunk_pages(pages(), **kwargs)
    second = chunk_pages(pages(), **kwargs)
    assert [chunk.id for chunk in first] == [chunk.id for chunk in second]
    assert len(first) >= 3
    assert first[0].page_start == first[0].page_end == 1
    assert first[-1].page_start == 2
    assert first[-1].text.endswith("CNC-450。")
    assert all(chunk.token_count == estimate_tokens(chunk.text) for chunk in first)


def test_chunk_id_depends_on_content_version_and_ordinal() -> None:
    base = stable_chunk_id("a" * 64, "v1", 0, "text")
    assert base != stable_chunk_id("b" * 64, "v1", 0, "text")
    assert base != stable_chunk_id("a" * 64, "v2", 0, "text")
    assert base != stable_chunk_id("a" * 64, "v1", 1, "text")
    assert base != stable_chunk_id("a" * 64, "v1", 0, "changed")
