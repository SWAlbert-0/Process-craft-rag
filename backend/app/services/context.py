import re

from app.services.chunking import estimate_tokens
from app.services.domain import Candidate, ContextItem


def _deduplication_key(text: str) -> str:
    return re.sub(r"\W+", "", text).lower()


def build_context(
    candidates: list[Candidate],
    token_budget: int = 5000,
    min_rerank_score: float = 0.0,
) -> list[ContextItem]:
    if token_budget <= 0:
        raise ValueError("上下文预算必须大于 0")
    selected: list[Candidate] = []
    keys: list[str] = []
    used_tokens = 0
    for candidate in candidates:
        score = candidate.rerank_score
        if score is not None and score < min_rerank_score:
            continue
        text = candidate.hit.text.strip()
        key = _deduplication_key(text)
        if not key or any(key in existing or existing in key for existing in keys):
            continue
        cost = estimate_tokens(text) + 24
        if selected and used_tokens + cost > token_budget:
            continue
        if not selected and cost > token_budget:
            continue
        selected.append(candidate)
        keys.append(key)
        used_tokens += cost
    return [
        ContextItem(label=index, candidate=candidate) for index, candidate in enumerate(selected, 1)
    ]


def format_context(items: list[ContextItem]) -> str:
    sections: list[str] = []
    for item in items:
        hit = item.candidate.hit
        pages = (
            str(hit.page_start)
            if hit.page_start == hit.page_end
            else f"{hit.page_start}-{hit.page_end}"
        )
        section = " > ".join(hit.section_path) or "未识别"
        sections.append(
            f"[{item.label}] 文档：{hit.document_name}；PDF 物理页码：{pages}；章节：{section}\n"
            f"<不可信原文数据>\n{hit.text}\n</不可信原文数据>"
        )
    return "\n\n".join(sections)
