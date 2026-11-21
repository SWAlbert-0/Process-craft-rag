import re

from app.services.domain import ContextItem

_CITATION_RE = re.compile(r"\[(\d+)\]")


class CitationValidationError(ValueError):
    pass


def citation_labels(text: str) -> list[int]:
    return [int(value) for value in _CITATION_RE.findall(text)]


def validate_citation_labels(labels: list[int], allowed_labels: set[int]) -> None:
    invalid = set(labels) - allowed_labels
    if invalid:
        raise CitationValidationError(f"模型输出了非法引用编号：{sorted(invalid)}")


def citations_for_labels(items: list[ContextItem], labels: list[int]) -> list[dict]:
    validate_citation_labels(labels, {item.label for item in items})
    used = set(labels)
    return [item.citation for item in items if item.label in used]
