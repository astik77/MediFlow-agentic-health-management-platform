"""
Hybrid Lexical (BM25) + Dense Vector Cosine Retriever with Reciprocal Rank Fusion (RRF)
and Zero-Tolerance SEC-003 Cross-Patient Isolation Verification.
"""
from __future__ import annotations

import math
import uuid
from collections import Counter
from dataclasses import dataclass

from mediflow.ai.rag.embedder import tokenize_clinical_text


class CrossPatientRetrievalViolationError(Exception):
    """SEC-003 / RAG-008: Raised if any candidate chunk violates patient ownership."""

    error_code = "sec003_cross_patient_retrieval_blocked"


@dataclass(slots=True)
class IndexedChunkCandidate:
    """In-memory candidate chunk paired with its stored vector and provenance."""

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    patient_id: uuid.UUID
    document_title: str
    document_type: str
    document_date: str | None
    page_start: int
    page_end: int
    section_heading: str | None
    content: str
    embedding_vector: list[float] | None
    embedding_model: str | None


@dataclass(slots=True)
class ScoredRagHit:
    """Final fused retrieval hit with score, match mode, and verifiable citation metadata."""

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    patient_id: uuid.UUID
    document_title: str
    document_type: str
    document_date: str | None
    page_start: int
    page_end: int
    section_heading: str | None
    snippet: str
    score: float
    lexical_score: float
    vector_score: float
    match_type: str  # hybrid | semantic | lexical


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity safely across equal-length vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b, strict=True))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def compute_bm25_scores(
    query: str,
    corpus_texts: list[str],
    *,
    k1: float = 1.5,
    b: float = 0.75,
) -> list[float]:
    """
    Okapi BM25 lexical relevance scoring over tokenized clinical documents.
    Uses synonym-expanded query terms with higher weight for exact query tokens.
    """
    if not corpus_texts:
        return []

    exact_q = tokenize_clinical_text(query, expand_synonyms=False)
    expanded_q = tokenize_clinical_text(query, expand_synonyms=True)
    if not expanded_q:
        return [0.0] * len(corpus_texts)

    exact_set = set(exact_q)
    docs_tokens = [tokenize_clinical_text(txt, expand_synonyms=False) for txt in corpus_texts]
    doc_lens = [len(t) for t in docs_tokens]
    avgdl = sum(doc_lens) / len(doc_lens) if doc_lens else 1.0
    avgdl = max(avgdl, 1.0)
    n_docs = len(corpus_texts)

    # Document frequency for query terms
    df: Counter[str] = Counter()
    for d_toks in docs_tokens:
        for term in set(d_toks):
            df[term] += 1

    scores: list[float] = []
    unique_query_terms = list(dict.fromkeys(expanded_q))

    for d_toks, dl in zip(docs_tokens, doc_lens, strict=True):
        tf = Counter(d_toks)
        doc_score = 0.0
        for term in unique_query_terms:
            freq = tf.get(term, 0)
            if freq == 0:
                continue
            term_df = df.get(term, 0)
            idf = math.log(1.0 + (n_docs - term_df + 0.5) / (term_df + 0.5))
            denom = freq + k1 * (1.0 - b + b * (dl / avgdl))
            term_weight = 1.0 if term in exact_set else 0.55
            doc_score += term_weight * idf * ((freq * (k1 + 1.0)) / denom)
        scores.append(round(doc_score, 6))

    return scores


def assert_patient_scoped_hits(
    hits: list[ScoredRagHit], expected_patient_id: uuid.UUID
) -> None:
    """
    SEC-003 / RAG-008 defense-in-depth invariant:
    Verifies every retrieved chunk belongs strictly to the authenticated patient.
    """
    for h in hits:
        if h.patient_id != expected_patient_id:
            raise CrossPatientRetrievalViolationError(
                "Blocked cross-patient chunk during RAG retrieval (SEC-003)."
            )


def _build_snippet(content: str, query: str, max_len: int = 320) -> str:
    """Extract a readable snippet centered around the first matching query term."""
    cleaned = " ".join(content.split())
    if len(cleaned) <= max_len:
        return cleaned
    terms = tokenize_clinical_text(query, expand_synonyms=False)
    low = cleaned.lower()
    pos = -1
    for t in terms:
        idx = low.find(t)
        if idx != -1:
            pos = idx
            break
    if pos == -1:
        return cleaned[:max_len].rstrip() + "..."
    start = max(0, pos - 90)
    end = min(len(cleaned), start + max_len)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(cleaned) else ""
    return f"{prefix}{cleaned[start:end].strip()}{suffix}"


def hybrid_rank_candidates(
    *,
    query: str,
    query_vector: list[float],
    candidates: list[IndexedChunkCandidate],
    expected_patient_id: uuid.UUID,
    top_k: int = 5,
    rrf_k: int = 60,
    min_vector_score: float = 0.14,
) -> list[ScoredRagHit]:
    """
    Combine Okapi BM25 lexical ranking and cosine vector similarity via
    Reciprocal Rank Fusion (RRF), strictly enforcing SEC-003 patient ownership.
    """
    if not candidates:
        return []

    # Defense-in-depth ownership check BEFORE ranking
    for cand in candidates:
        if cand.patient_id != expected_patient_id:
            raise CrossPatientRetrievalViolationError(
                "Foreign-patient chunk entered RAG candidate pool (SEC-003)."
            )

    corpus = [
        f"{c.document_title}\n{c.section_heading or ''}\n{c.content}"
        for c in candidates
    ]
    lex_scores = compute_bm25_scores(query, corpus)
    vec_scores = [
        round(cosine_similarity(query_vector, c.embedding_vector), 6)
        if c.embedding_vector
        else 0.0
        for c in candidates
    ]

    # Build rank maps (1-indexed) only for candidates with positive signal
    lex_ranked = sorted(
        [i for i, s in enumerate(lex_scores) if s > 0.0],
        key=lambda i: lex_scores[i],
        reverse=True,
    )
    vec_ranked = sorted(
        [i for i, s in enumerate(vec_scores) if s >= min_vector_score],
        key=lambda i: vec_scores[i],
        reverse=True,
    )

    lex_rank_pos = {idx: rank for rank, idx in enumerate(lex_ranked, start=1)}
    vec_rank_pos = {idx: rank for rank, idx in enumerate(vec_ranked, start=1)}

    eligible = sorted(set(lex_ranked) | set(vec_ranked))
    if not eligible:
        return []

    max_lex = max(lex_scores) if max(lex_scores) > 0 else 1.0
    hits: list[ScoredRagHit] = []

    for idx in eligible:
        c = candidates[idx]
        l_rank = lex_rank_pos.get(idx)
        v_rank = vec_rank_pos.get(idx)

        rrf = 0.0
        if l_rank is not None:
            rrf += 1.0 / (rrf_k + l_rank)
        if v_rank is not None:
            rrf += 1.0 / (rrf_k + v_rank)

        # Blend RRF with normalized raw scores so strong exact+semantic matches win ties
        norm_lex = lex_scores[idx] / max_lex if lex_scores[idx] > 0 else 0.0
        norm_vec = max(0.0, vec_scores[idx])
        combined = round((rrf * 30.0) + (0.35 * norm_lex) + (0.35 * norm_vec), 4)

        if l_rank is not None and v_rank is not None:
            match_type = "hybrid"
        elif v_rank is not None:
            match_type = "semantic"
        else:
            match_type = "lexical"

        hits.append(
            ScoredRagHit(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                patient_id=c.patient_id,
                document_title=c.document_title,
                document_type=c.document_type,
                document_date=c.document_date,
                page_start=c.page_start,
                page_end=c.page_end,
                section_heading=c.section_heading,
                snippet=_build_snippet(c.content, query),
                score=combined,
                lexical_score=round(lex_scores[idx], 4),
                vector_score=round(vec_scores[idx], 4),
                match_type=match_type,
            )
        )

    hits.sort(key=lambda h: (h.score, h.lexical_score, h.vector_score), reverse=True)
    top_hits = hits[:top_k]
    assert_patient_scoped_hits(top_hits, expected_patient_id)
    return top_hits
