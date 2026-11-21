from pathlib import Path

import pymupdf
import pytest

from app.services.pdf import PDFParseError, normalize_text, parse_pdf


def test_parse_real_a4_preserves_physical_pages() -> None:
    root = Path(__file__).parents[2]
    path = root / "docs/样例文件/01-第一次迭代/nist-ams-400-1-on-machine-measurement.pdf"
    pages = parse_pdf(path)
    assert len(pages) == 69
    assert [page.page for page in pages] == list(range(1, 70))
    assert all(page.normalized_text for page in pages)
    assert "on-machine" in pages[0].normalized_text.lower()


def test_normalization_conserves_numbers_and_units() -> None:
    text = "The spin-\nndle runs at 1200 rpm.\nTolerance ±0.05 mm\n\nNext paragraph"
    normalized = normalize_text(text)
    assert "1200 rpm" in normalized
    assert "±0.05 mm" in normalized
    assert "Next paragraph" in normalized


def test_rejects_pdf_without_text(tmp_path: Path) -> None:
    path = tmp_path / "empty.pdf"
    document = pymupdf.open()
    document.new_page()
    document.save(path)
    document.close()
    with pytest.raises(PDFParseError, match="OCR"):
        parse_pdf(path)


def test_rejects_non_pdf(tmp_path: Path) -> None:
    path = tmp_path / "bad.pdf"
    path.write_text("not a pdf", encoding="utf-8")
    with pytest.raises(PDFParseError, match="损坏"):
        parse_pdf(path)
