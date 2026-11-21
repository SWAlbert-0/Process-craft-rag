import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.errors import AppError
from app.models import Citation, Conversation, Message
from app.schemas import ConversationCreate, MessageRequest
from app.services.embeddings import ModelServiceError
from app.services.llm import ModelOutputError
from app.services.rag import DocumentNotReadyError, EmptyKnowledgeBaseError, RAGService

router = APIRouter(prefix="/conversations", tags=["conversations"])


def iso(value) -> str:
    return value.isoformat()


def message_dict(message: Message, citations: list[Citation]) -> dict:
    return {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "role": message.role,
        "status": message.status,
        "content": message.content,
        "structured_content": message.structured_content,
        "citations": [
            {
                "label": citation.label,
                "chunk_id": citation.chunk_id,
                "document_id": citation.document_id,
                "document_name": citation.document_name,
                "page_start": citation.page_start,
                "page_end": citation.page_end,
                "excerpt": citation.excerpt,
                "rerank_score": citation.rerank_score,
                "source_available": True,
            }
            for citation in citations
        ],
        "retrieval_diagnostics": message.retrieval_diagnostics,
        "run_config": message.run_config,
        "request_id": message.request_id,
        "created_at": iso(message.created_at),
    }


def get_conversation(db: Session, conversation_id: str) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    if not conversation or conversation.deleted_at:
        raise AppError(404, "NOT_FOUND", "会话不存在")
    return conversation


@router.post("", status_code=201)
def create_conversation(payload: ConversationCreate, db: Session = Depends(get_db)) -> dict:
    conversation = Conversation(
        title=payload.title,
        mode=payload.mode,
        document_filter=payload.document_ids,
    )
    db.add(conversation)
    db.commit()
    return {"id": conversation.id, "title": conversation.title, "mode": conversation.mode}


@router.get("/{conversation_id}")
def conversation_detail(conversation_id: str, db: Session = Depends(get_db)) -> dict:
    conversation = get_conversation(db, conversation_id)
    return {
        "id": conversation.id,
        "title": conversation.title,
        "mode": conversation.mode,
        "document_filter": conversation.document_filter,
    }


@router.get("/{conversation_id}/messages")
def list_messages(conversation_id: str, db: Session = Depends(get_db)) -> dict:
    get_conversation(db, conversation_id)
    messages = db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    ).all()
    items = []
    for message in messages:
        citations = db.scalars(
            select(Citation).where(Citation.message_id == message.id).order_by(Citation.label)
        ).all()
        items.append(message_dict(message, citations))
    return {"items": items, "total": len(items)}


@router.post("/{conversation_id}/messages")
async def create_message(
    conversation_id: str,
    payload: MessageRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    conversation = get_conversation(db, conversation_id)
    question = payload.content.strip()
    if not question:
        raise AppError(422, "VALIDATION_ERROR", "问题不能为空")
    if payload.client_request_id:
        existing = db.scalar(
            select(Message).where(
                Message.conversation_id == conversation.id,
                Message.client_request_id == payload.client_request_id,
            )
        )
        if existing:
            assistant = db.scalar(select(Message).where(Message.parent_message_id == existing.id))
            if assistant:
                citations = db.scalars(
                    select(Citation).where(Citation.message_id == assistant.id)
                ).all()
                return message_dict(assistant, citations)

    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=question,
        client_request_id=payload.client_request_id,
        request_id=str(uuid.uuid4()),
    )
    db.add(user_message)
    if conversation.title == "新会话":
        conversation.title = question[:60]
    db.commit()

    try:
        result = await RAGService(settings).answer(db, question, payload.mode, payload.document_ids)
    except EmptyKnowledgeBaseError as exc:
        raise AppError(409, "EMPTY_KNOWLEDGE_BASE", str(exc)) from exc
    except DocumentNotReadyError as exc:
        raise AppError(409, "DOCUMENT_NOT_READY", str(exc)) from exc
    except ModelServiceError as exc:
        failed = Message(
            conversation_id=conversation.id,
            parent_message_id=user_message.id,
            role="assistant",
            content=str(exc),
            status="failed",
            request_id=user_message.request_id,
        )
        db.add(failed)
        db.commit()
        code = (
            "OUTPUT_VALIDATION_FAILED" if isinstance(exc, ModelOutputError) else "MODEL_UNAVAILABLE"
        )
        raise AppError(502, code, str(exc)) from exc
    except ValueError as exc:
        raise AppError(502, "OUTPUT_VALIDATION_FAILED", "模型输出未通过引用或结构校验") from exc

    assistant = Message(
        conversation_id=conversation.id,
        parent_message_id=user_message.id,
        role="assistant",
        content=result.content,
        structured_content=result.structured_content,
        query_rewrite=question,
        model_name=settings.llm_model,
        run_config=result.run_config,
        retrieval_diagnostics=result.diagnostics,
        request_id=user_message.request_id,
    )
    db.add(assistant)
    db.flush()
    citations = [
        Citation(
            message_id=assistant.id,
            label=item["label"],
            chunk_id=item["chunk_id"],
            document_id=item["document_id"],
            index_version_id=result.run_config["index_version_id"],
            document_name=item["document_name"],
            page_start=item["page_start"],
            page_end=item["page_end"],
            excerpt=item["excerpt"],
            rerank_score=item["rerank_score"],
        )
        for item in result.citations
    ]
    db.add_all(citations)
    db.commit()
    response = message_dict(assistant, citations)
    response["usage"] = result.usage
    response["insufficient_evidence"] = result.insufficient_evidence
    return response
