"""
Local-First Embedding Engine for MEDIFLOW Patient-Specific RAG (Phase 7).

Primary backend: Ollama `nomic-embed-text` (768-dim, local CPU-friendly).
Automatic offline/test fallback: `LocalHashEmbedder` (256-dim deterministic
L2-normalized feature-hashed dense vector with medical synonym expansion).
Zero paid APIs, zero PyTorch downloads.
"""
from __future__ import annotations

import hashlib
import itertools
import math
import re
from dataclasses import dataclass

from mediflow.ai.providers.base import AIProviderError
from mediflow.ai.providers.ollama import OllamaProvider
from mediflow.core.config import get_settings

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:[./\-][a-z0-9]+)?")

# Lightweight deterministic clinical concept expansion for offline semantic matching
CLINICAL_SYNONYMS: dict[str, tuple[str, ...]] = {
    "sugar": ("glucose", "hba1c", "diabetes", "glycemic"),
    "glucose": ("sugar", "hba1c", "glycemic"),
    "hba1c": ("glucose", "sugar", "hemoglobin"),
    "diabetes": ("glucose", "hba1c", "metformin"),
    "anemia": ("hemoglobin", "haemoglobin", "rbc"),
    "hemoglobin": ("haemoglobin", "anemia", "cbc"),
    "haemoglobin": ("hemoglobin", "anemia", "cbc"),
    "kidney": ("creatinine", "urea", "renal", "egfr"),
    "renal": ("creatinine", "kidney", "urea"),
    "creatinine": ("kidney", "renal"),
    "liver": ("alt", "ast", "sgpt", "sgot", "bilirubin", "hepatic"),
    "thyroid": ("tsh", "t3", "t4", "thyroxine"),
    "tsh": ("thyroid", "thyroxine"),
    "cholesterol": ("lipid", "ldl", "hdl", "triglycerides", "atorvastatin"),
    "lipid": ("cholesterol", "ldl", "hdl", "triglycerides"),
    "heart": ("cardiopulmonary", "cardiothoracic", "bp", "pressure", "pulse"),
    "bp": ("blood", "pressure", "mmhg", "hypertension"),
    "pressure": ("bp", "mmhg", "hypertension"),
    "lung": ("pulmonary", "pneumonia", "chest", "respiratory", "xray"),
    "lungs": ("pulmonary", "pneumonia", "chest", "respiratory", "xray"),
    "chest": ("lung", "pulmonary", "cardiopulmonary", "xray", "radiology"),
    "xray": ("radiology", "chest", "radiograph", "imaging"),
    "infection": ("wbc", "antibiotic", "pneumonia", "fever"),
    "medication": ("prescription", "tablet", "tab", "metformin", "atorvastatin", "omeprazole"),
    "medicine": ("prescription", "tablet", "tab", "medication"),
    "hospital": ("discharge", "admission", "inpatient", "pneumonia"),
}

_STOPWORDS: frozenset[str] = frozenset(
    {
        "the",
        "and",
        "for",
        "with",
        "was",
        "were",
        "are",
        "have",
        "has",
        "had",
        "what",
        "when",
        "where",
        "show",
        "tell",
        "about",
        "from",
        "that",
        "this",
        "your",
        "does",
        "did",
        "into",
        "can",
        "you",
    }
)


def tokenize_clinical_text(text: str, *, expand_synonyms: bool = False) -> list[str]:
    """Tokenize text into lowercase clinical terms, optionally expanding synonyms."""
    raw_tokens = [
        tok for tok in _TOKEN_RE.findall(text.lower()) if len(tok) >= 2 and tok not in _STOPWORDS
    ]
    if not expand_synonyms:
        return raw_tokens

    expanded = list(raw_tokens)
    for tok in raw_tokens:
        syns = CLINICAL_SYNONYMS.get(tok)
        if syns:
            expanded.extend(syns)
    return expanded


@dataclass(slots=True)
class EmbedBatchResult:
    """Result from embedding a batch of texts."""

    vectors: list[list[float]]
    model_name: str
    dimensions: int


class LocalHashEmbedder:
    """
    Deterministic, zero-dependency 256-dimensional L2-normalized dense embedder.
    Hashes clinical unigrams, expanded synonyms, bigrams, and character 4-grams
    using signed feature hashing (Weinberger et al.) for fast CPU cosine similarity.
    """

    model_name: str = "local-hash-256-v1"
    dimensions: int = 256

    def embed_one(self, text: str, *, is_query: bool = False) -> list[float]:
        vec = [0.0] * self.dimensions
        tokens = tokenize_clinical_text(text, expand_synonyms=True)

        features: list[tuple[str, float]] = []
        base_tokens = tokenize_clinical_text(text, expand_synonyms=False)
        for tok in base_tokens:
            features.append((f"u:{tok}", 2.0))
            # Character 4-grams capture morphological variants (e.g. diabetic/diabetes)
            if len(tok) >= 5:
                for i in range(len(tok) - 3):
                    features.append((f"c:{tok[i : i + 4]}", 0.35))
        for tok in tokens[len(base_tokens) :]:
            features.append((f"s:{tok}", 1.1 if is_query else 0.7))
        for a, b in itertools.pairwise(base_tokens):
            features.append((f"b:{a}_{b}", 1.4))

        for feat, weight in features:
            digest = hashlib.blake2b(feat.encode("utf-8"), digest_size=8).digest()
            idx = int.from_bytes(digest[:4], "little") % self.dimensions
            sign = 1.0 if (digest[4] & 1) == 0 else -1.0
            vec[idx] += sign * weight

        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0.0:
            return [round(v / norm, 6) for v in vec]
        return vec

    def embed_batch(self, texts: list[str], *, is_query: bool = False) -> EmbedBatchResult:
        return EmbedBatchResult(
            vectors=[self.embed_one(t, is_query=is_query) for t in texts],
            model_name=self.model_name,
            dimensions=self.dimensions,
        )


def compute_content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class EmbeddingService:
    """
    Hybrid local embedder: uses Ollama `nomic-embed-text` when reachable,
    and falls back deterministically to `LocalHashEmbedder` when Ollama is offline.
    """

    def __init__(self, *, prefer_ollama: bool = True) -> None:
        self.prefer_ollama = prefer_ollama
        self.fallback = LocalHashEmbedder()

    async def embed_texts(
        self,
        texts: list[str],
        *,
        is_query: bool = False,
        force_local_fallback: bool = False,
    ) -> EmbedBatchResult:
        if not texts:
            return EmbedBatchResult(vectors=[], model_name=self.fallback.model_name, dimensions=0)

        if self.prefer_ollama and not force_local_fallback:
            settings = get_settings()
            ollama = OllamaProvider(
                base_url=settings.ollama_base_url,
                default_model=settings.ollama_default_model,
                embedding_model=settings.ollama_embedding_model,
                timeout_seconds=min(float(settings.ai_health_check_timeout_seconds) * 3.0, 2.0),
            )
            try:
                res = await ollama.embed(texts)
                if res.embeddings and len(res.embeddings) == len(texts):
                    # L2-normalize Ollama vectors for clean cosine dot product
                    normed: list[list[float]] = []
                    for vec in res.embeddings:
                        norm = math.sqrt(sum(v * v for v in vec))
                        if norm > 0.0:
                            normed.append([round(v / norm, 6) for v in vec])
                        else:
                            normed.append(vec)
                    return EmbedBatchResult(
                        vectors=normed,
                        model_name=res.model,
                        dimensions=res.dimensions,
                    )
            except AIProviderError:
                pass

        return self.fallback.embed_batch(texts, is_query=is_query)
