import hashlib
import re

from app.services.domain import ChunkData, PageText

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:[._+/-][A-Za-z0-9]+)*|[\u4e00-\u9fff]")


def estimate_tokens(text: str) -> int:
    return max(1, len(_TOKEN_RE.findall(text)))


def stable_chunk_id(content_sha256: str, version: str, ordinal: int, text: str) -> str:
    value = f"{content_sha256}:{version}:{ordinal}:{text}".encode()
    return hashlib.sha256(value).hexdigest()


def _split_oversize(text: str, target: int, overlap: int) -> list[str]:
    sentences = [part.strip() for part in re.split(r"(?<=[.!?。！？])\s+", text) if part.strip()]
    units = sentences if len(sentences) > 1 else [text]
    pieces: list[str] = []
    current = ""
    for unit in units:
        while len(unit) > target:
            if current:
                pieces.append(current)
                current = ""
            pieces.append(unit[:target])
            unit = unit[max(1, target - overlap) :]
        if not current:
            current = unit
        elif len(current) + len(unit) + 1 <= target:
            current = f"{current} {unit}"
        else:
            pieces.append(current)
            prefix = current[-overlap:] if overlap else ""
            current = f"{prefix} {unit}".strip()
    if current:
        pieces.append(current)
    return pieces


def _page_chunks(text: str, target: int, overlap: int) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        parts = (
            _split_oversize(paragraph, target, overlap) if len(paragraph) > target else [paragraph]
        )
        for part in parts:
            if not current:
                current = part
            elif len(current) + len(part) + 2 <= target:
                current = f"{current}\n\n{part}"
            else:
                chunks.append(current)
                prefix = current[-overlap:] if overlap else ""
                current = f"{prefix}\n\n{part}".strip() if prefix else part
    if current:
        chunks.append(current)
    return chunks


def _section_path(text: str) -> list[str]:
    first = text.splitlines()[0].strip() if text.splitlines() else ""
    if 2 <= len(first) <= 100 and not first.endswith((".", "。", ";", "；")):
        return [first]
    return []


def chunk_pages(
    pages: list[PageText],
    content_sha256: str,
    document_id: str,
    document_name: str,
    version: str = "paragraph-recursive-v1",
    target_chars: int = 900,
    overlap_chars: int = 120,
    min_chars: int = 120,
) -> list[ChunkData]:
    if target_chars <= overlap_chars or overlap_chars < 0:
        raise ValueError("分块长度必须大于重叠长度，且重叠长度不能为负数")

    chunks: list[ChunkData] = []
    for page in pages:
        if not page.normalized_text.strip():
            continue
        parts = _page_chunks(page.normalized_text, target_chars, overlap_chars)
        if len(parts) > 1 and len(parts[-1]) < min_chars:
            merged = f"{parts[-2]}\n\n{parts[-1]}"
            if len(merged) <= int(target_chars * 1.3):
                parts[-2:] = [merged]
        for text in parts:
            text = text.strip()
            if len(text) < min_chars and chunks:
                previous = chunks[-1]
                if previous.page_end == page.page:
                    merged_text = f"{previous.text}\n\n{text}"
                    chunks[-1] = ChunkData(
                        id=stable_chunk_id(content_sha256, version, previous.ordinal, merged_text),
                        document_id=document_id,
                        document_name=document_name,
                        ordinal=previous.ordinal,
                        text=merged_text,
                        page_start=previous.page_start,
                        page_end=page.page,
                        section_path=previous.section_path,
                        token_count=estimate_tokens(merged_text),
                    )
                    continue
            if not text:
                continue
            ordinal = len(chunks)
            chunks.append(
                ChunkData(
                    id=stable_chunk_id(content_sha256, version, ordinal, text),
                    document_id=document_id,
                    document_name=document_name,
                    ordinal=ordinal,
                    text=text,
                    page_start=page.page,
                    page_end=page.page,
                    section_path=_section_path(page.normalized_text),
                    token_count=estimate_tokens(text),
                )
            )
    if not chunks:
        raise ValueError("文档清洗后没有可索引分块")
    return chunks
