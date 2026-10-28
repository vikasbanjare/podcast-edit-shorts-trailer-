#!/usr/bin/env python3
"""Resolve LLM utterance-index candidates to source times and snap them to speech boundaries.

The LLM never writes seconds. It returns utterance indices (start_utt, end_utt). This script
maps those indices to word timestamps and then snaps the in/out points to:
  - the start of speech (optionally the end of a nearby silence),
  - a sentence-ending word within 3 seconds after the last word,
  - a short padding after the last word, capped by the next silence.

Input JSON:
{
  "utterances": [{"speaker": "Guest", "words": [{"w": "Hello", "s": 1.2, "e": 1.6}, ...]}, ...],
  "silences":   [[start_s, end_s], ...],            # optional, from ffmpeg silencedetect
  "candidates": [{"id": "c1", "start_utt": 3, "end_utt": 7, ...}, ...]
}

Output JSON: {"candidates": [...]} with start, end, duration_s, status and snap_notes added.
Status is "ok", "too_short" or "too_long"; duration_band is "short" (<=30 s),
"standard" (<=60 s) or "extended" (<=90 s). Nothing here sets verified=true; that needs an audio check.
"""
import argparse
import json
import sys

SENTENCE_END = (".", "?", "!", "।")  # includes Devanagari danda for Hindi transcripts
TRAILING_CLOSERS = "\"'”’)]"  # quotes/brackets that may follow the sentence mark
MIN_DURATION = 15.0
MAX_DURATION = 90.0
SHORT_MAX = 30.0
STANDARD_MAX = 60.0
START_PAD = 0.15
END_PAD = 0.30
SENTENCE_LOOKAHEAD = 3.0
SILENCE_LOOKBACK = 1.0


def _is_sentence_end(word):
    return word["w"].rstrip().rstrip(TRAILING_CLOSERS).endswith(SENTENCE_END)


def duration_band(duration):
    if duration <= SHORT_MAX:
        return "short"
    if duration <= STANDARD_MAX:
        return "standard"
    return "extended"


def snap_candidate(cand, utterances, silences):
    """Return a copy of cand with snapped start/end. Raises ValueError on bad indices."""
    n = len(utterances)
    s_idx, e_idx = int(cand["start_utt"]), int(cand["end_utt"])
    if not (0 <= s_idx <= e_idx < n):
        raise ValueError(f"{cand.get('id')}: utterance range {s_idx}-{e_idx} outside 0-{n - 1}")

    first_words = utterances[s_idx]["words"]
    last_words = utterances[e_idx]["words"]
    if not first_words or not last_words:
        raise ValueError(f"{cand.get('id')}: empty utterance at the range edge")

    notes = []
    first = first_words[0]
    last = last_words[-1]

    # Flatten words after the first word so we can look ahead for a sentence end.
    all_words = [w for u in utterances[s_idx:e_idx + 1] for w in u["words"]]

    # --- start: prefer the end of a silence that ends just before the first word ---
    start = first["s"] - START_PAD
    for s0, s1 in silences:
        if first["s"] - SILENCE_LOOKBACK <= s1 <= first["s"]:
            start = s1
            notes.append("start snapped to silence end")
            break
    start = max(0.0, start)

    # --- end: extend to a sentence end within 3 seconds if the last word is mid-sentence ---
    end_word = last
    if not _is_sentence_end(last):
        # Look at words after the last word in the following utterances.
        following = [w for u in utterances[e_idx + 1:] for w in u["words"]]
        for w in following:
            if w["s"] - last["e"] > SENTENCE_LOOKAHEAD:
                break
            if _is_sentence_end(w):
                end_word = w
                notes.append("end extended to sentence end")
                break

    end = end_word["e"] + END_PAD
    # Do not run into the next silence if it starts before the padded end.
    for s0, s1 in silences:
        if end_word["e"] <= s0 < end:
            end = s0 + 0.05
            notes.append("end capped at silence start")
            break

    duration = end - start
    if duration < MIN_DURATION:
        status = "too_short"
    elif duration > MAX_DURATION:
        status = "too_long"
    else:
        status = "ok"

    out = dict(cand)
    out.update({
        "start": round(start, 2),
        "end": round(end, 2),
        "duration_s": round(duration, 2),
        "status": status,
        "duration_band": duration_band(duration),
        "snap_notes": notes,
        "word_count": len(all_words),
    })
    return out


def resolve_all(data):
    utterances = data["utterances"]
    silences = [tuple(x) for x in data.get("silences", [])]
    results = []
    for cand in data["candidates"]:
        try:
            results.append(snap_candidate(cand, utterances, silences))
        except ValueError as exc:
            results.append({**cand, "status": "invalid", "error": str(exc)})
    return {"candidates": results}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="JSON file with utterances, silences and candidates")
    ap.add_argument("-o", "--output", help="Write output here (default: stdout)")
    args = ap.parse_args()

    with open(args.input, encoding="utf-8") as fh:
        data = json.load(fh)
    result = resolve_all(data)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    else:
        sys.stdout.write(text + "\n")


if __name__ == "__main__":
    main()
