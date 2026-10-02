import json
from pathlib import Path

from eval.metrics import (
    Gold,
    Hit,
    gate_rates,
    hit_at_k,
    parse_judge,
    percentile,
    recall_at_k,
    reciprocal_rank,
)

GOLD = [Gold("sd.md", "Push CDNs"), Gold("sd.md", "Pull CDNs")]
HITS = [
    Hit("sd.md", "Primer > Cache"),
    Hit("sd.md", "Primer > Content delivery network > Pull CDNs"),
    Hit("other.md", "Push CDNs"),  # right section name, wrong file: not relevant
    Hit("sd.md", "Primer > Content delivery network > Push CDNs"),
]


def test_ranking_metrics():
    assert hit_at_k(HITS, GOLD, 1) == 0.0
    assert hit_at_k(HITS, GOLD, 2) == 1.0
    assert reciprocal_rank(HITS, GOLD, 5) == 0.5
    assert recall_at_k(HITS, GOLD, 2) == 0.5
    assert recall_at_k(HITS, GOLD, 4) == 1.0
    assert recall_at_k(HITS, [], 4) == 0.0


def test_gate_rates():
    rates = gate_rates([0.9, 0.01, None], [0.001, 0.5], threshold=0.02)
    assert rates == {"refusal_accuracy": 0.5, "false_refusal_rate": 2 / 3}


def test_percentile():
    assert percentile([5, 1, 3, 2, 4], 50) == 3
    assert percentile([5, 1, 3, 2, 4], 95) == 5
    assert percentile([], 95) == 0.0


def test_parse_judge_handles_noise_and_clamps():
    assert parse_judge('Sure! {"correctness": 0.8, "faithfulness": 1.4, "reason": "ok"}') == {
        "correctness": 0.8,
        "faithfulness": 1.0,
        "reason": "ok",
    }
    assert parse_judge("no json here") is None
    assert parse_judge('{"correctness": "high"}') is None


def test_dataset_is_well_formed():
    path = Path(__file__).resolve().parents[1] / "eval" / "dataset.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids))
    assert sum(1 for r in rows if r["gold"]) >= 30
    assert sum(1 for r in rows if not r["gold"]) >= 8
    for r in rows:
        assert r["question"].strip()
        assert (r["expected_answer"] is None) == (not r["gold"])
        for g in r["gold"]:
            assert set(g) == {"file", "section"}
