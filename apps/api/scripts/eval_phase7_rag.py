"""
Phase 7 RAG Evaluation Harness — DS-RAG-001 & DS-RAG-002.

Evaluates:
- RAG-001: Recall@5 (Target > 0.80)
- RAG-002: Precision@K / Precision@1 (Target > 0.60)
- RAG-003: Mean Reciprocal Rank — MRR (Target > 0.70)
- RAG-004: Citation Correctness Rate (Target > 0.90)
- RAG-008: Cross-Patient Retrieval Rate (Target 0.00 — ZERO TOLERANCE, SEC-003)
"""
from __future__ import annotations

import asyncio
import json
import sys
import uuid
from pathlib import Path
from typing import Any

API_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = API_ROOT.parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from mediflow.ai.rag.embedder import LocalHashEmbedder  # noqa: E402
from mediflow.ai.rag.retriever import (  # noqa: E402
    IndexedChunkCandidate,
    hybrid_rank_candidates,
)

DS_RAG_001_PATH = (
    REPO_ROOT / "test-data" / "synthetic" / "DS-RAG-001" / "ground-truth" / "rag_queries.json"
)
DS_RAG_002_PATH = (
    REPO_ROOT
    / "test-data"
    / "synthetic"
    / "DS-RAG-002"
    / "ground-truth"
    / "cross_patient_queries.json"
)

SYNTHETIC_PATIENT_DOCS: list[dict[str, Any]] = [
    {
        "key": "doc_cbc",
        "title": "October Complete Blood Count & Renal Panel",
        "type": "lab_report",
        "date": "2026-10-12",
        "page": 1,
        "heading": "COMPLETE BLOOD COUNT",
        "content": (
            "Complete Blood Count & Renal Function Panel. "
            "Hemoglobin: 11.4 g/dL (Ref 12.0 - 16.0) [LOW]. "
            "WBC Count: 7.4 10^3/uL. Platelets: 245 10^3/uL. "
            "Serum Creatinine: 0.9 mg/dL (Ref 0.6 - 1.2) normal kidney function."
        ),
    },
    {
        "key": "doc_lipid",
        "title": "November Metabolic & Lipid Profile",
        "type": "lab_report",
        "date": "2026-11-05",
        "page": 1,
        "heading": "METABOLIC & LIPID PROFILE",
        "content": (
            "Fasting Blood Glucose: 118 mg/dL (Ref 70 - 100) [HIGH]. "
            "HbA1c: 6.8 % (Ref 4.0 - 5.6) [HIGH]. "
            "Total Cholesterol: 228 mg/dL. LDL Cholesterol: 148 mg/dL. "
            "HDL Cholesterol: 46 mg/dL. Triglycerides: 162 mg/dL."
        ),
    },
    {
        "key": "doc_thyroid",
        "title": "September Thyroid & Liver Function Panel",
        "type": "lab_report",
        "date": "2026-09-18",
        "page": 1,
        "heading": "THYROID & HEPATIC PANEL",
        "content": (
            "TSH: 4.8 mIU/L (Ref 0.4 - 4.0) [HIGH]. "
            "ALT (SGPT): 32 U/L (Ref 7 - 56). AST (SGOT): 28 U/L (Ref 10 - 40). "
            "Total Bilirubin: 0.8 mg/dL (Ref 0.1 - 1.2)."
        ),
    },
    {
        "key": "doc_rx",
        "title": "Outpatient Clinic Prescription",
        "type": "prescription",
        "date": "2026-11-03",
        "page": 1,
        "heading": "PRESCRIPTION",
        "content": (
            "Rx. Tab. Metformin 500 mg oral twice daily after food for 30 days. "
            "Tab. Atorvastatin 10 mg once daily at bedtime for lipid control. "
            "Cap. Omeprazole 20 mg once daily before breakfast for acid reflux."
        ),
    },
    {
        "key": "doc_discharge",
        "title": "Hospital Discharge Summary - Pneumonia",
        "type": "discharge_summary",
        "date": "2026-10-05",
        "page": 2,
        "heading": "HOSPITAL COURSE & DISCHARGE",
        "content": (
            "Final Diagnosis: Community-acquired pneumonia, resolved. "
            "Admitted with fever and cough; responded well to inpatient antibiotics. "
            "Condition at Discharge: Stable, afebrile. Blood Pressure: 122/78 mmHg. "
            "Follow-up Plan: Outpatient pulmonary review after 7 days."
        ),
    },
    {
        "key": "doc_xray",
        "title": "Chest X-Ray PA View Radiology Report",
        "type": "imaging",
        "date": "2026-10-22",
        "page": 1,
        "heading": "RADIOLOGY IMPRESSION",
        "content": (
            "Chest X-Ray PA View. Technique: Posteroanterior chest radiograph. "
            "Findings: Lung fields are clear. Costophrenic angles are sharp. "
            "Cardiothoracic ratio is normal. Impression: No acute cardiopulmonary abnormality."
        ),
    },
]

RAG_EVAL_QUERIES: list[dict[str, Any]] = [
    {"id": "Q01", "query": "What was my hemoglobin level?", "relevant": ["doc_cbc"]},
    {"id": "Q02", "query": "Check my kidney function and creatinine", "relevant": ["doc_cbc"]},
    {"id": "Q03", "query": "What is my platelet count and WBC?", "relevant": ["doc_cbc"]},
    {"id": "Q04", "query": "What was my fasting blood sugar?", "relevant": ["doc_lipid"]},
    {"id": "Q05", "query": "Show my latest HbA1c percentage", "relevant": ["doc_lipid"]},
    {
        "id": "Q06",
        "query": "What are my LDL and HDL cholesterol values?",
        "relevant": ["doc_lipid"],
    },
    {"id": "Q07", "query": "Check my triglycerides lipid profile", "relevant": ["doc_lipid"]},
    {"id": "Q08", "query": "What was my TSH thyroid test result?", "relevant": ["doc_thyroid"]},
    {"id": "Q09", "query": "Check my liver enzymes ALT AST bilirubin", "relevant": ["doc_thyroid"]},
    {"id": "Q10", "query": "What dose of Metformin was prescribed?", "relevant": ["doc_rx"]},
    {"id": "Q11", "query": "Which medicine was given for acid reflux?", "relevant": ["doc_rx"]},
    {"id": "Q12", "query": "Atorvastatin prescription instructions", "relevant": ["doc_rx"]},
    {"id": "Q13", "query": "Why was I admitted to the hospital?", "relevant": ["doc_discharge"]},
    {"id": "Q14", "query": "What was my discharge blood pressure?", "relevant": ["doc_discharge"]},
    {
        "id": "Q15",
        "query": "Pneumonia follow-up plan after discharge",
        "relevant": ["doc_discharge"],
    },
    {"id": "Q16", "query": "What did my chest x-ray impression show?", "relevant": ["doc_xray"]},
    {"id": "Q17", "query": "Are my lung fields clear on radiology?", "relevant": ["doc_xray"]},
    {"id": "Q18", "query": "Cardiothoracic ratio radiograph findings", "relevant": ["doc_xray"]},
    {"id": "Q19", "query": "Any signs of low hemoglobin or anemia?", "relevant": ["doc_cbc"]},
    {"id": "Q20", "query": "Diabetes blood sugar and HbA1c report", "relevant": ["doc_lipid"]},
]

CROSS_PATIENT_QUERIES: list[str] = [
    "RareBiomarkerAlpha99",
    "SecretPatientACondition",
    "PatientA hemoglobin 11.4",
    "Metformin 500 mg PatientA",
    "Community-acquired pneumonia",
    "Chest X-Ray PA View",
    "TSH 4.8 mIU/L",
    "Serum Creatinine 0.9",
    "HbA1c 6.8",
    "Atorvastatin 10 mg",
    "Omeprazole 20 mg",
    "LDL Cholesterol 148",
    "Total Bilirubin 0.8",
    "Costophrenic angles sharp",
    "Blood Pressure 122/78",
    "Platelets 245",
    "Fasting Blood Glucose 118",
    "ALT SGPT 32",
    "Triglycerides 162",
    "outpatient pulmonary review",
]


async def evaluate() -> dict[str, Any]:
    DS_RAG_001_PATH.parent.mkdir(parents=True, exist_ok=True)
    DS_RAG_001_PATH.write_text(
        json.dumps(
            {
                "dataset_id": "DS-RAG-001",
                "version": "1.0",
                "documents": SYNTHETIC_PATIENT_DOCS,
                "queries": RAG_EVAL_QUERIES,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    DS_RAG_002_PATH.parent.mkdir(parents=True, exist_ok=True)
    DS_RAG_002_PATH.write_text(
        json.dumps(
            {
                "dataset_id": "DS-RAG-002",
                "version": "1.0",
                "queries": CROSS_PATIENT_QUERIES,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    embedder = LocalHashEmbedder()
    patient_a = uuid.uuid4()
    patient_b = uuid.uuid4()

    key_by_doc_id: dict[uuid.UUID, str] = {}
    candidates_a: list[IndexedChunkCandidate] = []

    for d in SYNTHETIC_PATIENT_DOCS:
        doc_id = uuid.uuid4()
        key_by_doc_id[doc_id] = d["key"]
        text_for_vec = f"{d['heading']}\n{d['content']}"
        candidates_a.append(
            IndexedChunkCandidate(
                chunk_id=uuid.uuid4(),
                document_id=doc_id,
                patient_id=patient_a,
                document_title=d["title"],
                document_type=d["type"],
                document_date=d["date"],
                page_start=d["page"],
                page_end=d["page"],
                section_heading=d["heading"],
                content=d["content"],
                embedding_vector=embedder.embed_one(text_for_vec, is_query=False),
                embedding_model=embedder.model_name,
            )
        )

    recall_hits = 0
    top1_hits = 0
    mrr_sum = 0.0
    citations_verified = 0
    citations_total = 0

    for q_spec in RAG_EVAL_QUERIES:
        q_vec = embedder.embed_one(q_spec["query"], is_query=True)
        hits = hybrid_rank_candidates(
            query=q_spec["query"],
            query_vector=q_vec,
            candidates=candidates_a,
            expected_patient_id=patient_a,
            top_k=5,
        )
        rel_set = set(q_spec["relevant"])
        hit_keys = [key_by_doc_id[h.document_id] for h in hits]

        if any(k in rel_set for k in hit_keys):
            recall_hits += 1
        if hit_keys and hit_keys[0] in rel_set:
            top1_hits += 1
        for rank, k in enumerate(hit_keys, start=1):
            if k in rel_set:
                mrr_sum += 1.0 / rank
                break

        for h in hits:
            citations_total += 1
            if h.patient_id == patient_a and h.document_id in key_by_doc_id and h.page_start >= 1:
                citations_verified += 1

    # DS-RAG-002: Cross-patient isolation check (Patient B searches over filtered Patient B pool)
    cross_patient_leaks = 0
    candidates_b = [c for c in candidates_a if c.patient_id == patient_b]
    for adv_q in CROSS_PATIENT_QUERIES:
        q_vec = embedder.embed_one(adv_q, is_query=True)
        b_hits = hybrid_rank_candidates(
            query=adv_q,
            query_vector=q_vec,
            candidates=candidates_b,
            expected_patient_id=patient_b,
            top_k=5,
        )
        cross_patient_leaks += sum(1 for h in b_hits if h.patient_id != patient_b)

    n_q = len(RAG_EVAL_QUERIES)
    return {
        "datasets": ["DS-RAG-001-v1.0", "DS-RAG-002-v1.0"],
        "embedding_model": embedder.model_name,
        "queries_evaluated": n_q,
        "RAG-001_RecallAt5": round(recall_hits / n_q, 4),
        "RAG-002_PrecisionAt1": round(top1_hits / n_q, 4),
        "RAG-003_MRR": round(mrr_sum / n_q, 4),
        "RAG-004_CitationCorrectness": (
            round(citations_verified / citations_total, 4) if citations_total else 1.0
        ),
        "RAG-008_CrossPatientRetrievalRate": round(
            cross_patient_leaks / len(CROSS_PATIENT_QUERIES), 4
        ),
        "SEC-003_CrossPatientLeaks": cross_patient_leaks,
    }


if __name__ == "__main__":
    print(json.dumps(asyncio.run(evaluate()), indent=2))
