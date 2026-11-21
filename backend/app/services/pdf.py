import re
import unicodedata
from pathlib import Path

import pymupdf

from app.services.domain import PageText


class PDFParseError(ValueError):
    pass


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ").replace("\u200b", "")
    text = re.sub(r"(?<=[A-Za-z])-\n(?=[a-z])", "", text)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    output: list[str] = []
    for line in lines:
        if not line:
            if output and output[-1]:
                output.append("")
            continue
        starts_structure = bool(re.match(r"^(?:[-•*]|\d+(?:\.\d+)*[.)]?)\s", line))
        if (
            output
            and output[-1]
            and not starts_structure
            and not re.search(r"[.!?:;。！？：；]$", output[-1])
            and not line[0].isupper()
        ):
            output[-1] = f"{output[-1]} {line}"
        else:
            output.append(line)
    return "\n".join(output).strip()


def parse_pdf(path: Path, max_pages: int = 400) -> list[PageText]:
    try:
        document = pymupdf.open(path)
    except Exception as exc:
        raise PDFParseError("PDF 文件损坏或格式不受支持") from exc

    try:
        if document.needs_pass or document.is_encrypted:
            raise PDFParseError("加密 PDF 暂不支持，请先解除加密")
        if document.page_count == 0:
            raise PDFParseError("PDF 没有可解析页面")
        if document.page_count > max_pages:
            raise PDFParseError(f"PDF 页数超过当前上限 {max_pages}")

        pages: list[PageText] = []
        for index, page in enumerate(document):
            raw = page.get_text("text", sort=True)
            pages.append(
                PageText(page=index + 1, raw_text=raw, normalized_text=normalize_text(raw))
            )
    except PDFParseError:
        raise
    except Exception as exc:
        raise PDFParseError("PDF 页面解析失败") from exc
    finally:
        document.close()

    if sum(len(page.normalized_text) for page in pages) < 100:
        raise PDFParseError("未提取到足够正文；扫描件需要 OCR，本轮尚未启用")
    return pages
