import os
import uuid

import pytest

from app.services.domain import ChunkData
from app.services.vector_store import QdrantStore

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_QDRANT_TESTS") != "1", reason="set RUN_QDRANT_TESTS=1 with Qdrant running"
)


async def test_real_qdrant_round_trip() -> None:
    store = QdrantStore(os.getenv("QDRANT_URL", "http://localhost:6333"))
    version_id = str(uuid.uuid4())
    collection = f"kb_default__iv_{version_id}"
    chunk = ChunkData("chunk-a", "doc-a", "process.pdf", 0, "spindle calibration", 4, 4)
    try:
        await store.create_version(collection, version_id, [chunk], [[1.0, 0.0, 0.0]], 3)
        assert await store.chunk_ids(collection) == {"chunk-a"}
        hits = await store.search(collection, [1.0, 0.0, 0.0], 5)
        assert hits[0].chunk_id == "chunk-a"
        assert hits[0].page_start == 4
        assert hits[0].text == "spindle calibration"
    finally:
        await store.delete(collection)
        await store.close()
