import argparse
import json
import os
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).parents[2]
EVIDENCE_DIR = ROOT / "docs" / "评估记录" / "I1"
QUESTION_SET = EVIDENCE_DIR / "冒烟题集.json"
RAW_OUTPUT = EVIDENCE_DIR / "原始输出.json"
A4_PATH = ROOT / "docs" / "样例文件" / "01-第一次迭代" / "nist-ams-400-1-on-machine-measurement.pdf"


def request(client: httpx.Client, method: str, path: str, **kwargs) -> dict:
    response = client.request(method, path, **kwargs)
    if response.status_code >= 400:
        raise RuntimeError(
            f"{method} {path} returned HTTP {response.status_code}: {response.text[:300]}"
        )
    return response.json()


def ensure_document(client: httpx.Client, content_sha256: str) -> dict:
    documents = request(client, "GET", "/documents", params={"page_size": 100})["items"]
    existing = next((item for item in documents if item["content_sha256"] == content_sha256), None)
    if existing:
        document = existing
    else:
        with A4_PATH.open("rb") as handle:
            result = request(
                client,
                "POST",
                "/documents",
                files={"file": (A4_PATH.name, handle, "application/pdf")},
            )
        document = result["document"]

    deadline = time.monotonic() + 1200
    while document["status"] not in {"ready", "failed"}:
        if time.monotonic() > deadline:
            raise TimeoutError("A4 ingestion did not finish within 20 minutes")
        time.sleep(2)
        document = request(client, "GET", f"/documents/{document['id']}")
    if document["status"] != "ready":
        raise RuntimeError(f"A4 ingestion failed: {document['failure_message']}")
    return document


def all_chunks(client: httpx.Client, document_id: str) -> list[dict]:
    items: list[dict] = []
    page = 1
    while True:
        result = request(
            client,
            "GET",
            f"/documents/{document_id}/chunks",
            params={"page": page, "page_size": 100},
        )
        items.extend(result["items"])
        if len(items) >= result["total"]:
            return items
        page += 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the frozen I1 A4 smoke set against a real API"
    )
    parser.add_argument("--api", default=os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1"))
    parser.add_argument("--output", type=Path, default=RAW_OUTPUT, help="Raw result JSON path")
    args = parser.parse_args()
    question_set = json.loads(QUESTION_SET.read_text(encoding="utf-8"))
    run_id = str(uuid.uuid4())
    records: list[dict] = []
    started_at = datetime.now(UTC).isoformat()

    with httpx.Client(base_url=args.api, timeout=240) as client:
        document = ensure_document(client, question_set["document_sha256"])
        chunks = all_chunks(client, document["id"])
        chunk_by_id = {chunk["id"]: chunk for chunk in chunks}
        for question in question_set["questions"]:
            conversation = request(
                client,
                "POST",
                "/conversations",
                json={
                    "title": question["question_id"],
                    "mode": question["mode"],
                    "document_ids": [document["id"]],
                },
            )
            expected_chunks = [
                chunk["id"]
                for chunk in chunks
                if any(
                    chunk["page_start"] <= page <= chunk["page_end"]
                    for page in question["expected_pages"]
                )
            ]
            started = time.perf_counter()
            answer = request(
                client,
                "POST",
                f"/conversations/{conversation['id']}/messages",
                json={
                    "content": question["question"],
                    "mode": question["mode"],
                    "document_ids": [document["id"]],
                    "client_request_id": f"{run_id}-{question['question_id']}",
                },
            )
            diagnostics = answer["retrieval_diagnostics"]
            citations = answer["citations"]
            actual_pages = {
                page
                for citation in citations
                for page in range(citation["page_start"], citation["page_end"] + 1)
            }
            checks = {
                "both_retrieval_routes_nonempty": bool(diagnostics["dense"])
                and bool(diagnostics["sparse"]),
                "fusion_and_rerank_nonempty": bool(diagnostics["fusion"])
                and bool(diagnostics["rerank"]),
                "citation_snapshots_match_chunks": all(
                    citation["chunk_id"] in chunk_by_id
                    and citation["excerpt"] == chunk_by_id[citation["chunk_id"]]["text"]
                    for citation in citations
                ),
                "expected_page_cited": bool(actual_pages & set(question["expected_pages"]))
                if question["expected_pages"]
                else None,
                "refusal_flag_when_required": answer.get("insufficient_evidence") is True
                if question["should_refuse"]
                else None,
            }
            records.append(
                {
                    "question": question,
                    "relevant_chunk_ids_from_annotated_pages": expected_chunks,
                    "answer": answer,
                    "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                    "automated_checks": checks,
                    "manual_review": {
                        "status": "pending",
                        "correctness": None,
                        "completeness": None,
                        "citation_correctness": None,
                        "expression": None,
                        "serious_failure": None,
                        "notes": "",
                    },
                }
            )
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(
                    {
                        "run_id": run_id,
                        "started_at": started_at,
                        "api_base_url": args.api,
                        "document": document,
                        "dataset_id": question_set["dataset_id"],
                        "results": records,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            print(f"{question['question_id']}: saved; manual review pending")


if __name__ == "__main__":
    main()
