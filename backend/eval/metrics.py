"""Pure metric functions (no DB, no LLM) so they can be unit-tested."""

import json
import re
from dataclasses import dataclass
from statistics import median


@dataclass(frozen=True)
class Gold:
    file: str
    section: str  # case-insensitive substring of the chunk's heading path


@dataclass(frozen=True)
class Hit:
    filename: str
    section: str | None


def is_relevant(hit: Hit, gold: list[Gold]) -> bool:
    return any(_matches(hit, g) for g in gold)


def _matches(hit: Hit, g: Gold) -> bool:
    return hit.filename == g.file and g.section.lower() in (hit.section or "").lower()


def hit_at_k(hits: list[Hit], gold: list[Gold], k: int) -> float:
    return 1.0 if any(is_relevant(h, gold) for h in hits[:k]) else 0.0


def recall_at_k(hits: list[Hit], gold: list[Gold], k: int) -> float:
    """Fraction of gold sections covered by the top-k (multi-part questions need all parts)."""
    if not gold:
        return 0.0
    return sum(1 for g in gold if any(_matches(h, g) for h in hits[:k])) / len(gold)


def reciprocal_rank(hits: list[Hit], gold: list[Gold], k: int) -> float:
    for rank, h in enumerate(hits[:k], start=1):
        if is_relevant(h, gold):
            return 1.0 / rank
    return 0.0


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, round(p / 100 * (len(ordered) - 1))))
    return ordered[idx]


def p50(values: list[float]) -> float:
    return median(values) if values else 0.0


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def gate_rates(
    top_scores_answerable: list[float | None],
    top_scores_unanswerable: list[float | None],
    threshold: float,
) -> dict[str, float]:
    """How well "refuse if best score < threshold" separates answerable from unanswerable."""

    def refused(score: float | None) -> bool:
        return score is None or score < threshold

    correct_refusals = mean([1.0 if refused(s) else 0.0 for s in top_scores_unanswerable])
    false_refusals = mean([1.0 if refused(s) else 0.0 for s in top_scores_answerable])
    return {"refusal_accuracy": correct_refusals, "false_refusal_rate": false_refusals}


_JSON_OBJ = re.compile(r"\{.*\}", re.DOTALL)


def parse_judge(text: str) -> dict[str, float | str] | None:
    """Extract {"correctness": x, "faithfulness": y, "reason": "..."} from a judge reply."""
    match = _JSON_OBJ.search(text or "")
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        out: dict[str, float | str] = {}
        for key in ("correctness", "faithfulness"):
            out[key] = max(0.0, min(1.0, float(data[key])))
        out["reason"] = str(data.get("reason", ""))[:300]
        return out
    except (ValueError, KeyError, TypeError):
        return None
