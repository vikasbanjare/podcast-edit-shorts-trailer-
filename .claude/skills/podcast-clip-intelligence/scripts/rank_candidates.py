#!/usr/bin/env python3
"""Apply honesty and arc gates, score candidates on the tuned rubric, de-duplicate and rank.

Each candidate needs six 0-100 scores and four boolean gates (see references/rubric.md):

{
  "candidates": [{
      "id": "c1", "title": "...", "start": 120.4, "end": 165.2, "status": "ok",
      "scores": {"hook": 85, "standalone": 90, "emotion": 60, "value": 70, "payoff": 80, "pacing": 75},
      "gates": {"honesty": true, "arc_complete": true, "standalone_context": true, "no_greeting_or_ad": true},
      "notes": "..."
  }, ...]
}

Output: ranked list. Killed candidates keep their reason so the honesty-gate log can be written.
"""
import argparse
import json
import sys

WEIGHTS = {
    "hook": 0.25,
    "standalone": 0.25,
    "emotion": 0.15,
    "value": 0.15,
    "payoff": 0.10,
    "pacing": 0.10,
}
GATES = ["honesty", "arc_complete", "standalone_context", "no_greeting_or_ad"]
DEFAULT_THRESHOLD = 60.0
MAX_OVERLAP_RATIO = 0.5  # drop the lower-scored clip if this much of the shorter one overlaps


def weighted_score(scores):
    missing = [k for k in WEIGHTS if k not in scores]
    if missing:
        raise ValueError(f"missing score(s): {', '.join(missing)}")
    total = 0.0
    for key, weight in WEIGHTS.items():
        value = float(scores[key])
        if not 0 <= value <= 100:
            raise ValueError(f"score '{key}' out of range 0-100: {value}")
        total += value * weight
    return round(total, 1)


def overlap_ratio(a, b):
    start = max(a["start"], b["start"])
    end = min(a["end"], b["end"])
    if end <= start:
        return 0.0
    shorter = min(a["end"] - a["start"], b["end"] - b["start"])
    return (end - start) / shorter if shorter > 0 else 0.0


def rank(candidates, threshold=DEFAULT_THRESHOLD, top_n=None):
    killed, scored = [], []
    for cand in candidates:
        reasons = []
        if cand.get("status") not in (None, "ok"):
            reasons.append(f"timing: {cand['status']}")
        gates = cand.get("gates", {})
        for gate in GATES:
            if not gates.get(gate, False):
                reasons.append(f"gate failed: {gate}")
        if reasons:
            killed.append({**cand, "kill_reasons": reasons})
            continue
        try:
            score = weighted_score(cand.get("scores", {}))
        except ValueError as exc:
            killed.append({**cand, "kill_reasons": [str(exc)]})
            continue
        if score < threshold:
            killed.append({**cand, "kill_reasons": [f"score {score} below threshold {threshold}"]})
            continue
        scored.append({**cand, "score": score})

    scored.sort(key=lambda c: c["score"], reverse=True)

    kept = []
    dropped_as_duplicate = []
    for cand in scored:
        clash = next((k for k in kept if overlap_ratio(cand, k) > MAX_OVERLAP_RATIO), None)
        if clash is None:
            kept.append(cand)
        else:
            dropped_as_duplicate.append({**cand, "kill_reasons": [f"overlaps {clash['id']}"]})

    if top_n is not None:
        kept = kept[:top_n]
    return {"ranked": kept, "killed": killed + dropped_as_duplicate}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="JSON file with scored candidates")
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    ap.add_argument("--top", type=int, default=12, help="Maximum clips to keep (default 12)")
    ap.add_argument("-o", "--output", help="Write output here (default: stdout)")
    args = ap.parse_args()

    with open(args.input, encoding="utf-8") as fh:
        data = json.load(fh)
    result = rank(data["candidates"], threshold=args.threshold, top_n=args.top)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    else:
        sys.stdout.write(text + "\n")


if __name__ == "__main__":
    main()
