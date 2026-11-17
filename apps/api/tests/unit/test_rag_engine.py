"""
Phase 7 Unit Tests — Hybrid RAG Embedder, BM25 + Cosine RRF Retriever, and SEC-003 Guard.
"""
from __future__ import annotations

import uuid

import pytest

from mediflow.ai.rag.embedder import LocalHashEmbedder
from mediflow.ai.rag.retriever import (
    CrossPatientRetrievalViolationError,
    IndexedChunkCandidate,
    cosine_similarity,
    hybrid_rank_candidates,
)


class TestRagEmbedderAndRetriever:
    def test_local_hash_embedder_captures_clinical_synonyms(self) -> None:
        emb = LocalHashEmbedder()
        q_sugar = emb.embed_one("fasting blood sugar", is_query=True)
        v_glucose = emb.embed_one("Fasting Blood Glucose 118 mg/dL HbA1c 6.8%")
        v_xray = emb.embed_one("Chest X-Ray PA View lung fields clear costophrenic angles")

        sim_glucose = cosine_similarity(q_sugar, v_glucose)
        sim_xray = cosine_similarity(q_sugar, v_xray)
        assert sim_glucose > sim_xray
        assert sim_glucose > 0.25

    def test_hybrid_rank_candidates_prefers_relevant_document(self) -> None:
        emb = LocalHashEmbedder()
        pid = uuid.uuid4()
        c_thyroid = IndexedChunkCandidate(
            chunk_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            patient_id=pid,
            document_title="Thyroid Panel",
            document_type="lab_report",
            document_date="2026-10-01",
            page_start=1,
            page_end=1,
            section_heading="THYROID",
            content="TSH: 4.8 mIU/L (Ref 0.4 - 4.0) [HIGH]. Thyroid function panel.",
            embedding_vector=emb.embed_one("TSH: 4.8 mIU/L Thyroid function panel"),
            embedding_model=emb.model_name,
        )
        c_xray = IndexedChunkCandidate(
            chunk_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            patient_id=pid,
            document_title="Chest X-Ray",
            document_type="imaging",
            document_date="2026-10-10",
            page_start=1,
            page_end=1,
            section_heading="IMPRESSION",
            content="Lung fields clear. No acute cardiopulmonary abnormality.",
            embedding_vector=emb.embed_one("Lung fields clear no cardiopulmonary abnormality"),
            embedding_model=emb.model_name,
        )

        hits = hybrid_rank_candidates(
            query="What was my thyroid TSH value?",
            query_vector=emb.embed_one("What was my thyroid TSH value?", is_query=True),
            candidates=[c_xray, c_thyroid],
            expected_patient_id=pid,
            top_k=5,
        )
        assert len(hits) >= 1
        assert hits[0].document_id == c_thyroid.document_id
        assert hits[0].match_type == "hybrid"

    def test_sec003_defense_in_depth_blocks_foreign_candidate(self) -> None:
        emb = LocalHashEmbedder()
        patient_a = uuid.uuid4()
        patient_b = uuid.uuid4()

        foreign_cand = IndexedChunkCandidate(
            chunk_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            patient_id=patient_b,
            document_title="Patient B Private Doc",
            document_type="lab_report",
            document_date="2026-11-01",
            page_start=1,
            page_end=1,
            section_heading=None,
            content="Hemoglobin 13.5 g/dL",
            embedding_vector=emb.embed_one("Hemoglobin 13.5 g/dL"),
            embedding_model=emb.model_name,
        )

        with pytest.raises(CrossPatientRetrievalViolationError):
            hybrid_rank_candidates(
                query="Hemoglobin",
                query_vector=emb.embed_one("Hemoglobin", is_query=True),
                candidates=[foreign_cand],
                expected_patient_id=patient_a,
                top_k=5,
            )
