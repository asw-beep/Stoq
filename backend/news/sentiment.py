"""FinBERT sentiment scorer.

The model (ProsusAI/finbert, ~500 MB) is lazy-loaded on first use and cached
as a module-level singleton. HuggingFace downloads to HF_HOME, which is
mounted as a named Docker volume so the download survives container rebuilds.

Input: article headline (optionally concatenated with summary for richer signal).
Output: one of "positive" | "negative" | "neutral" + confidence score (0–1).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from transformers import Pipeline

logger = logging.getLogger(__name__)

_MODEL_ID = "ProsusAI/finbert"
_pipeline: "Pipeline | None" = None


def _get_pipeline() -> "Pipeline":
    global _pipeline
    if _pipeline is None:
        from transformers import pipeline

        logger.info("Loading FinBERT model %s (first-time download may take a minute)", _MODEL_ID)
        _pipeline = pipeline(
            "text-classification",
            model=_MODEL_ID,
            tokenizer=_MODEL_ID,
            device=-1,  # CPU
            top_k=1,
        )
        logger.info("FinBERT loaded")
    return _pipeline


@dataclass
class SentimentResult:
    label: str   # "positive" | "negative" | "neutral"
    score: float  # 0–1


def score(text: str) -> SentimentResult:
    """Score a piece of financial text with FinBERT."""
    pipe = _get_pipeline()
    # pipeline returns [[{"label": ..., "score": ...}]] with top_k=1
    result = pipe(text[:512], truncation=True)[0][0]
    return SentimentResult(label=result["label"].lower(), score=round(result["score"], 4))


def score_batch(texts: list[str]) -> list[SentimentResult]:
    """Score multiple texts in one forward pass (more efficient than looping)."""
    pipe = _get_pipeline()
    truncated = [t[:512] for t in texts]
    results = pipe(truncated, truncation=True, batch_size=16)
    return [SentimentResult(label=r[0]["label"].lower(), score=round(r[0]["score"], 4)) for r in results]
