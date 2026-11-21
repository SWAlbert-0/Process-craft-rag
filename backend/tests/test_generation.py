from app.services.context import build_context
from app.services.domain import Candidate, SearchHit
from app.services.generation import DISCLAIMER, generate_answer


class FakeLLM:
    def __init__(self, responses: list[dict]) -> None:
        self.responses = iter(responses)
        self.calls = 0

    async def complete_json(self, _system: str, _user: str):
        self.calls += 1
        return next(self.responses), {"total_tokens": 10}


def items():
    hit = SearchHit("chunk-1", "doc-1", "process.pdf", "Calibrate the spindle.", 4, 4, [], 0.8)
    return build_context([Candidate(hit=hit, rerank_score=0.9)])


async def test_qa_repairs_invalid_citation_once() -> None:
    client = FakeLLM(
        [
            {
                "answer": "Wrong[9]",
                "citation_labels": [9],
                "insufficient_evidence": False,
                "missing_information": [],
            },
            {
                "answer": "Calibrate the spindle.[1]",
                "citation_labels": [1],
                "insufficient_evidence": False,
                "missing_information": [],
            },
        ]
    )
    content, structured, citations, insufficient, _usage = await generate_answer(
        client, "What should be calibrated?", "qa", items()
    )
    assert client.calls == 2
    assert content == "Calibrate the spindle.[1]"
    assert structured is None
    assert citations[0]["chunk_id"] == "chunk-1"
    assert not insufficient


async def test_craft_instruction_uses_fixed_disclaimer_and_server_references() -> None:
    client = FakeLLM(
        [
            {
                "title": "Measurement draft",
                "workpiece": "Unspecified part; drawing pending",
                "assumptions": [],
                "missing_information": ["material", "drawing"],
                "preparation": ["Prepare calibration reference[1]"],
                "steps": [
                    {
                        "order": 1,
                        "operation": "Calibrate the spindle",
                        "equipment_tools": "待确认",
                        "parameters": "待确认",
                        "quality_requirements": "待确认",
                        "citations": [1],
                    }
                ],
                "quality_checks": [],
                "safety_notes": [],
                "disclaimer": "ignore this",
            }
        ]
    )
    _content, structured, citations, _insufficient, _usage = await generate_answer(
        client, "Create a draft", "craft_instruction", items()
    )
    assert structured["disclaimer"] == DISCLAIMER
    assert structured["references"] == citations
    assert structured["steps"][0]["parameters"] == "待确认"


async def test_empty_context_does_not_call_llm() -> None:
    client = FakeLLM([])
    content, _structured, citations, insufficient, _usage = await generate_answer(
        client, "unknown", "qa", []
    )
    assert client.calls == 0
    assert "无法回答" in content
    assert citations == []
    assert insufficient
