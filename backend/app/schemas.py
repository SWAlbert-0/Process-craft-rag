from typing import Literal

from pydantic import BaseModel, Field


class QAResult(BaseModel):
    answer: str
    citation_labels: list[int] = Field(default_factory=list)
    insufficient_evidence: bool = False
    missing_information: list[str] = Field(default_factory=list)


class CraftStep(BaseModel):
    order: int
    operation: str
    equipment_tools: str = "待确认"
    parameters: str = "待确认"
    quality_requirements: str = "待确认"
    citations: list[int] = Field(default_factory=list)


class EvidenceText(BaseModel):
    text: str
    citations: list[int] = Field(default_factory=list)


class CraftInstruction(BaseModel):
    title: str
    workpiece: str
    assumptions: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    preparation: list[str] = Field(default_factory=list)
    steps: list[CraftStep] = Field(default_factory=list)
    quality_checks: list[EvidenceText] = Field(default_factory=list)
    safety_notes: list[EvidenceText] = Field(default_factory=list)
    disclaimer: str = "AI 辅助生成的工艺建议，必须由工艺人员审核后方可使用。"


class CitationResponse(BaseModel):
    label: int
    chunk_id: str
    document_id: str
    document_name: str
    page_start: int
    page_end: int
    excerpt: str
    rerank_score: float | None = None
    source_available: bool = True


class MessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    mode: Literal["qa", "craft_instruction"] = "qa"
    document_ids: list[str] | None = Field(default=None, max_length=50)
    client_request_id: str | None = Field(default=None, max_length=100)


class ConversationCreate(BaseModel):
    title: str = Field(default="新会话", max_length=200)
    mode: Literal["qa", "craft_instruction"] = "qa"
    document_ids: list[str] = Field(default_factory=list)
