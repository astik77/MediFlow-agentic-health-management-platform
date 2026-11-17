"""
Patient-Specific Hybrid RAG Service (Phase 7).

Manages:
- Automatic & on-demand chunk embedding indexing (`document_embeddings`)
- Strictly patient-scoped hybrid BM25 + cosine vector RRF retrieval (`SEC-003`)
- Zero-tolerance defense-in-depth ownership verification (`RAG-008 = 0.00`)
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from mediflow.ai.rag.embedder import EmbeddingService, compute_content_hash
from mediflow.ai.rag.retriever import (
    IndexedChunkCandidate,
    ScoredRagHit,
    hybrid_rank_candidates,
)
from mediflow.core.logging import get_logger
from mediflow.modules.documents.models import Document, DocumentChunk, DocumentEmbedding
from mediflow.modules.patients.models import PatientProfile

logger = get_logger(__name__)


class RagService:
    """Patient-scoped hybrid RAG indexing and retrieval service."""

    @staticmethod
    async def index_document_chunks(
        *,
        db: AsyncSession,
        document_id: uuid.UUID,
        patient_id: uuid.UUID,
        embedder: EmbeddingService | None = None,
    ) -> dict[str, Any]:
        """
        Generate and persist embeddings for all chunks belonging to a single document.
        Replaces prior embeddings for that document cleanly (idempotent).
        """
        emb_service = embedder or EmbeddingService()

        chunks = list(
            (
                await db.execute(
                    select(DocumentChunk)
                    .where(
                        DocumentChunk.document_id == document_id,
                        DocumentChunk.patient_id == patient_id,
                    )
                    .order_by(DocumentChunk.chunk_index.asc())
                )
            )
            .scalars()
            .all()
        )

        # Wipe old embeddings for this document before inserting fresh ones
        await db.execute(
            delete(DocumentEmbedding).where(
                DocumentEmbedding.document_id == document_id,
                DocumentEmbedding.patient_id == patient_id,
            )
        )

        if not chunks:
            return {"indexed_chunks": 0, "embedding_model": None, "dimensions": 0}

        texts = [
            f"{c.section_heading}\n{c.content}" if c.section_heading else c.content
            for c in chunks
        ]
        batch = await emb_service.embed_texts(texts, is_query=False)

        for chunk, vec in zip(chunks, batch.vectors, strict=True):
            db.add(
                DocumentEmbedding(
                    id=uuid.uuid4(),
                    chunk_id=chunk.id,
                    document_id=document_id,
                    patient_id=patient_id,
                    embedding_model=batch.model_name,
                    dimensions=batch.dimensions,
                    embedding_vector=vec,
                    content_hash=compute_content_hash(chunk.content),
                )
            )

        await db.flush()
        logger.info(
            "rag_document_indexed",
            document_id=str(document_id),
            patient_id=str(patient_id),
            chunks=len(chunks),
            embedding_model=batch.model_name,
            dimensions=batch.dimensions,
        )
        return {
            "indexed_chunks": len(chunks),
            "embedding_model": batch.model_name,
            "dimensions": batch.dimensions,
        }

    @staticmethod
    async def reindex_patient_documents(
        *,
        db: AsyncSession,
        patient: PatientProfile,
        embedder: EmbeddingService | None = None,
    ) -> dict[str, Any]:
        """Re-embed all active (non-archived) processed documents for the authenticated patient."""
        emb_service = embedder or EmbeddingService()
        docs = list(
            (
                await db.execute(
                    select(Document).where(
                        Document.patient_id == patient.id,
                        Document.is_archived.is_(False),
                    )
                )
            )
            .scalars()
            .all()
        )
        total_chunks = 0
        last_model: str | None = None
        last_dims = 0
        docs_indexed = 0

        for doc in docs:
            res = await RagService.index_document_chunks(
                db=db,
                document_id=doc.id,
                patient_id=patient.id,
                embedder=emb_service,
            )
            if res["indexed_chunks"] > 0:
                docs_indexed += 1
                total_chunks += int(res["indexed_chunks"])
                last_model = res["embedding_model"]
                last_dims = int(res["dimensions"])

        await db.commit()
        return {
            "documents_indexed": docs_indexed,
            "chunks_indexed": total_chunks,
            "embedding_model": last_model or emb_service.fallback.model_name,
            "dimensions": last_dims or emb_service.fallback.dimensions,
        }

    @staticmethod
    async def search(
        *,
        db: AsyncSession,
        patient: PatientProfile,
        query: str,
        top_k: int = 5,
        document_type: str | None = None,
        embedder: EmbeddingService | None = None,
    ) -> tuple[list[ScoredRagHit], str]:
        """
        Execute strictly patient-scoped hybrid RAG retrieval across active documents.
        - Enforces WHERE patient_id = authenticated_patient.id AND is_archived = False.
        - Ensures all chunks use vectors matching the active query embedder model.
        - Verifies SEC-003 zero-cross-patient invariant before returning results.
        """
        emb_service = embedder or EmbeddingService()

        # Strictly enclose patient_id on BOTH DocumentChunk and Document (SEC-003)
        stmt = (
            select(DocumentChunk, Document, DocumentEmbedding)
            .join(Document, DocumentChunk.document_id == Document.id)
            .outerjoin(DocumentEmbedding, DocumentEmbedding.chunk_id == DocumentChunk.id)
            .where(
                DocumentChunk.patient_id == patient.id,
                Document.patient_id == patient.id,
                Document.is_archived.is_(False),
            )
        )
        if document_type:
            stmt = stmt.where(Document.document_type == document_type)

        rows = (await db.execute(stmt)).all()
        if not rows:
            return [], emb_service.fallback.model_name

        # Embed query using active embedder (Ollama nomic-embed-text or deterministic local)
        q_batch = await emb_service.embed_texts([query], is_query=True)
        query_vec = q_batch.vectors[0]
        active_model = q_batch.model_name

        candidates: list[IndexedChunkCandidate] = []
        for chunk, doc, emb in rows:
            # If stored vector exists and matches active model dimensions, reuse it;
            # otherwise compute compatible vector on-the-fly with fallback embedder
            vec: list[float] | None = None
            emb_model: str | None = None
            if (
                emb is not None
                and emb.embedding_model == active_model
                and emb.dimensions == len(query_vec)
            ):
                vec = emb.embedding_vector
                emb_model = emb.embedding_model
            elif active_model == emb_service.fallback.model_name:
                text_for_vec = (
                    f"{chunk.section_heading}\n{chunk.content}"
                    if chunk.section_heading
                    else chunk.content
                )
                vec = emb_service.fallback.embed_one(text_for_vec, is_query=False)
                emb_model = emb_service.fallback.model_name

            candidates.append(
                IndexedChunkCandidate(
                    chunk_id=chunk.id,
                    document_id=doc.id,
                    patient_id=chunk.patient_id,
                    document_title=doc.title,
                    document_type=doc.document_type,
                    document_date=doc.document_date.isoformat() if doc.document_date else None,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    section_heading=chunk.section_heading,
                    content=chunk.content,
                    embedding_vector=vec,
                    embedding_model=emb_model,
                )
            )

        hits = hybrid_rank_candidates(
            query=query,
            query_vector=query_vec,
            candidates=candidates,
            expected_patient_id=patient.id,
            top_k=top_k,
        )
        return hits, active_model
