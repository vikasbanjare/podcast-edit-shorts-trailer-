#!/usr/bin/env python3
"""Convert a transcript export into the utterance list resolve_and_snap.py expects.

Accepted inputs (detected from the extension / content):
  .json  Whisper / faster-whisper / WhisperX output: {"segments": [{"start", "end", "text", "speaker"?,
         "words": [{"word", "start", "end"}]}]}. Word timestamps are kept exactly (best).
  .srt   Captions, e.g. exported from Premiere's Text panel. SRT has no word times, so words are spread
         evenly across each caption and flagged "approximate_words": true. Snapped cut points are then
         approximate and MUST be checked against the media before anything is marked verified.

A leading "Speaker 1:" / "Host:" label in a caption or segment becomes the speaker.
Times must be on the same timeline as the Premiere source sequence. Pass --offset to shift them
(e.g. when the transcript came from a media file that starts later in the sequence).

Usage: transcript_to_utterances.py input.(srt|json) -o utterances.json [--offset 0.0]
Output: {"utterances": [...], "approximate_words": bool}
"""
import argparse
import json
import re
import sys

SPEAKER = re.compile(r"^\s*([A-Za-z][\w .'-]{0,30}):\s+")
SRT_TIME = re.compile(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)")


def _secs(h, m, s, ms):
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")[:3]) / 1000


def _split_speaker(text, default=None):
    match = SPEAKER.match(text)
    if match:
        return match.group(1).strip(), text[match.end():]
    return default, text


def even_words(text, start, end):
    tokens = text.split()
    if not tokens:
        return []
    step = (end - start) / len(tokens)
    return [{"w": t, "s": round(start + i * step, 3), "e": round(start + (i + 1) * step, 3)}
            for i, t in enumerate(tokens)]


def from_srt(text, offset=0.0):
    utts = []
    for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n").strip()):
        lines = [l for l in block.split("\n") if l.strip()]
        times = next((SRT_TIME.search(l) for l in lines if SRT_TIME.search(l)), None)
        if not times:
            continue
        g = times.groups()
        start, end = _secs(*g[:4]) + offset, _secs(*g[4:]) + offset
        body = " ".join(l.strip() for l in lines[lines.index(times.string) + 1:])
        body = re.sub(r"<[^>]+>", "", body)
        speaker, body = _split_speaker(body)
        words = even_words(body, start, end)
        if words:
            utts.append({"speaker": speaker or (utts[-1]["speaker"] if utts else None), "words": words})
    return {"utterances": utts, "approximate_words": True}


def from_whisper(data, offset=0.0):
    utts, approx = [], False
    for seg in data.get("segments", []):
        speaker, text = _split_speaker(seg.get("text", ""), seg.get("speaker"))
        if seg.get("words"):
            words = [{"w": w.get("word", w.get("text", "")).strip(),
                      "s": round(float(w["start"]) + offset, 3), "e": round(float(w["end"]) + offset, 3)}
                     for w in seg["words"] if w.get("start") is not None and w.get("end") is not None]
            words = [w for w in words if w["w"]]
        else:
            approx = True
            words = even_words(text, float(seg["start"]) + offset, float(seg["end"]) + offset)
        if words:
            utts.append({"speaker": speaker, "words": words})
    return {"utterances": utts, "approximate_words": approx}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--offset", type=float, default=0.0, help="Seconds to add to every time")
    args = ap.parse_args()
    with open(args.input, encoding="utf-8-sig") as fh:
        raw = fh.read()
    if args.input.lower().endswith(".json"):
        result = from_whisper(json.loads(raw), args.offset)
    else:
        result = from_srt(raw, args.offset)
    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)
    n = len(result["utterances"])
    note = " (approximate word times: verify cuts against media)" if result["approximate_words"] else ""
    print(f"wrote {args.output}: {n} utterances{note}")
    return 0 if n else 1


if __name__ == "__main__":
    sys.exit(main())
