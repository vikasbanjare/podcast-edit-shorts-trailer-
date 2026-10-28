#!/usr/bin/env python3
"""Turn a podcast-clip-intelligence EDL into a Premiere Pro cut plan.

The plan lists one new sequence per Short and per trailer, each with the source segments to lift
from the user's source sequence, in timeline order, with times as seconds, Premiere ticks and
SMPTE timecode, snapped to whole frames (in-points round down, out-points round up so no word is
clipped). Driving Premiere is left to the MCP; this script only does the arithmetic and naming.

Usage:
  build_premiere_plan.py edl.json --source-sequence "EP12 Multicam" [--fps 25] [--prefix EP12]
                         [--include-unverified] [-o plan.json]

Sequence names: <PREFIX>_SHORT_<NN>_<slug> and <PREFIX>_TRAILER_<NN>_<slug>, plus "_UNVERIFIED"
when any part is unverified. Names are unique within the plan.
"""
import argparse
import json
import math
import re
import sys
import unicodedata

TICKS_PER_SECOND = 254016000000  # Premiere Pro's internal time base
NTSC_RATES = {23.976: 24, 29.97: 30, 59.94: 60}


def nominal_fps(fps):
    """Integer frame count per timecode second (NTSC rates use the rounded rate, non-drop-frame)."""
    for rate, nominal in NTSC_RATES.items():
        if abs(fps - rate) < 0.01:
            return nominal
    if abs(fps - round(fps)) > 1e-6:
        raise ValueError(f"unsupported frame rate {fps}")
    return int(round(fps))


def exact_fps(fps):
    for rate, nominal in NTSC_RATES.items():
        if abs(fps - rate) < 0.01:
            return nominal * 1000 / 1001
    return float(fps)


def snap(seconds, fps, direction):
    """Snap to a frame boundary: 'down' for in-points, 'up' for out-points. Returns the frame index."""
    frames = seconds * exact_fps(fps)
    eps = 1e-6  # treat values a hair off a frame boundary as on it
    return int(math.floor(frames + eps)) if direction == "down" else int(math.ceil(frames - eps))


def frame_to_seconds(frame, fps):
    return frame / exact_fps(fps)


def timecode(frame, fps):
    n = nominal_fps(fps)
    ff = frame % n
    total_s = frame // n
    return f"{total_s // 3600:02d}:{total_s // 60 % 60:02d}:{total_s % 60:02d}:{ff:02d}"


def time_fields(prefix, frame, fps):
    sec = frame_to_seconds(frame, fps)
    return {f"{prefix}_s": round(sec, 6), f"{prefix}_ticks": int(round(sec * TICKS_PER_SECOND)),
            f"{prefix}_tc": timecode(frame, fps), f"{prefix}_frame": frame}


def slug(text, limit=32):
    text = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode()
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return text[:limit].rstrip("-") or "untitled"


def _segments(parts, fps):
    """parts: list of dicts with start/end (source seconds) + metadata. Lays them end to end from 0."""
    out, cursor = [], 0
    for part in parts:
        src_in = snap(part["start"], fps, "down")
        src_out = snap(part["end"], fps, "up")
        if src_out <= src_in:
            raise ValueError(f"empty segment {part.get('label')}: {part['start']}-{part['end']}")
        length = src_out - src_in
        seg = {"label": part.get("label"), "speaker": part.get("speaker"), "dialogue": part.get("dialogue")}
        seg.update(time_fields("src_in", src_in, fps))
        seg.update(time_fields("src_out", src_out, fps))
        seg.update(time_fields("timeline_in", cursor, fps))
        seg.update(time_fields("timeline_out", cursor + length, fps))
        seg["duration_s"] = round(frame_to_seconds(length, fps), 3)
        for key in ("role", "transition", "shot", "audio", "on_screen_text"):
            if part.get(key):
                seg[key] = part[key]
        out.append(seg)
        cursor += length
    return out, cursor


def build_plan(edl, source_sequence, fps, prefix=None, include_unverified=False):
    prefix = slug(prefix or edl.get("episode_title") or "EP", 64).replace("-", "").upper()[:12] or "EP"
    sequences, skipped, used = [], [], set()

    def unique(name):
        base, n = name, 2
        while name in used:
            name = f"{base}_{n}"
            n += 1
        used.add(name)
        return name

    def add(kind, number, item_id, title, parts, verified, width, height, extra):
        if not verified and not include_unverified:
            skipped.append({"id": item_id, "reason": "not verified"})
            return
        try:
            segs, total = _segments(parts, fps)
        except ValueError as exc:
            skipped.append({"id": item_id, "reason": str(exc)})
            return
        name = f"{prefix}_{kind.upper()}_{number:02d}_{slug(title or item_id)}" + ("" if verified else "_UNVERIFIED")
        markers = [{"name": s["label"] or f"segment {i}", "comment": s.get("dialogue") or "",
                    "time_s": s["timeline_in_s"], "time_ticks": s["timeline_in_ticks"], "time_tc": s["timeline_in_tc"]}
                   for i, s in enumerate(segs, 1)]
        seq = {"name": unique(name), "kind": kind, "id": item_id, "verified": verified,
               "frame": {"width": width, "height": height}, "segments": segs, "markers": markers}
        seq.update(time_fields("total", total, fps))
        seq.update(extra)
        sequences.append(seq)

    shorts = [c for c in edl.get("clips", []) if c.get("type", "short") == "short"]
    for n, clip in enumerate(shorts, 1):
        if clip.get("start") is None or clip.get("end") is None:
            skipped.append({"id": clip["id"], "reason": "no timecodes (dialogue anchor only)"})
            continue
        part = {"start": clip["start"], "end": clip["end"], "label": clip.get("title") or clip["id"],
                "speaker": clip.get("speaker"), "dialogue": clip.get("dialogue")}
        add("short", n, clip["id"], clip.get("title"), [part], clip.get("verified") is True,
            clip.get("width") or 1080, clip.get("height") or 1920,
            {k: clip[k] for k in ("upload_title", "added_value", "caption_script", "series", "notes") if clip.get(k)})

    trailers = edl.get("trailers") or ([edl["trailer"]] if edl.get("trailer") else [])
    for n, trailer in enumerate(trailers, 1):
        tid = trailer.get("id") or f"trailer-{n:02d}"
        beats = sorted(trailer.get("beats", []), key=lambda b: b["sequence"])
        missing = [b["sequence"] for b in beats if b.get("start") is None or b.get("end") is None]
        if missing:
            skipped.append({"id": tid, "reason": f"beats without timecodes: {missing}"})
            continue
        parts = [{**b, "label": f"beat {b['sequence']}" + (f" {b['role']}" if b.get("role") else "")} for b in beats]
        add("trailer", n, tid, trailer.get("concept") or tid, parts,
            all(b.get("verified") is True for b in beats),
            trailer.get("width") or 1920, trailer.get("height") or 1080,
            {"non_chronological": any(b2["start"] < b1["start"] for b1, b2 in zip(beats, beats[1:]))})

    return {"source_sequence": source_sequence, "source_media": edl.get("source_media"), "fps": fps,
            "ticks_per_second": TICKS_PER_SECOND, "sequences": sequences, "skipped": skipped}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("edl")
    ap.add_argument("--source-sequence", required=True, help="Name of the Premiere sequence holding the full episode")
    ap.add_argument("--fps", type=float, default=None, help="Source sequence frame rate (default: EDL 'fps' or 25)")
    ap.add_argument("--prefix", help="Sequence name prefix (default from episode_title)")
    ap.add_argument("--include-unverified", action="store_true", help="Plan unverified items, named *_UNVERIFIED")
    ap.add_argument("-o", "--output")
    args = ap.parse_args()

    with open(args.edl, encoding="utf-8") as fh:
        edl = json.load(fh)
    fps = args.fps or edl.get("fps") or 25
    plan = build_plan(edl, args.source_sequence, fps, args.prefix, args.include_unverified)
    text = json.dumps(plan, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    else:
        sys.stdout.write(text + "\n")
    for s in plan["skipped"]:
        print(f"skip {s['id']}: {s['reason']}", file=sys.stderr)


if __name__ == "__main__":
    main()
