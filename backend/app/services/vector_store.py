import uuid

from qdrant_client import AsyncQdrantClient, models

from app.services.domain import ChunkData, SearchHit


class QdrantStore:
    def __init__(self, url: str) -> None:
        self.client = AsyncQdrantClient(url=url, timeout=30)

    async def ready(self) -> bool:
        try:
            await self.client.get_collections()
            return True
        except Exception:
            return False

    async def create_version(
        self,
        collection: str,
        index_version_id: str,
        chunks: list[ChunkData],
        vectors: list[list[float]],
        dimensions: int,
    ) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("向量数量与分块数量不一致")
        if await self.client.collection_exists(collection):
            await self.client.delete_collection(collection)
        await self.client.create_collection(
            collection_name=collection,
            vectors_config=models.VectorParams(size=dimensions, distance=models.Distance.COSINE),
        )
        points = []
        for chunk, vector in zip(chunks, vectors, strict=True):
            if len(vector) != dimensions:
                raise ValueError("嵌入向量维度与配置不一致")
            point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{index_version_id}:{chunk.id}"))
            points.append(
                models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=chunk.payload(index_version_id),
                )
            )
        for start in range(0, len(points), 64):
            await self.client.upsert(
                collection_name=collection,
                points=points[start : start + 64],
                wait=True,
            )

    async def chunk_ids(self, collection: str) -> set[str]:
        result: set[str] = set()
        offset = None
        while True:
            points, offset = await self.client.scroll(
                collection_name=collection,
                limit=256,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            result.update(point.payload["chunk_id"] for point in points)
            if offset is None:
                return result

    async def search(
        self,
        collection: str,
        vector: list[float],
        top_k: int,
        document_ids: list[str] | None = None,
    ) -> list[SearchHit]:
        query_filter = None
        if document_ids:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id", match=models.MatchAny(any=document_ids)
                    )
                ]
            )
        response = await self.client.query_points(
            collection_name=collection,
            query=vector,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        )
        return [
            SearchHit.from_payload(point.payload, point.score, rank)
            for rank, point in enumerate(response.points, start=1)
        ]

    async def delete(self, collection: str) -> None:
        if await self.client.collection_exists(collection):
            await self.client.delete_collection(collection)

    async def close(self) -> None:
        await self.client.close()
