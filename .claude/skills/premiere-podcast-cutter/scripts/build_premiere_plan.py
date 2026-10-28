#!/usr/bin/env python3
"""Turn a podcast-clip-intelligence EDL into a Premiere Pro cut plan.

The plan lists one new sequence per Short and per trailer, each with the source segments to lift
from the user's source sequence, in timeline order, with times as seconds, Premiere ticks and
SMPTE timecode, snapped to whole frames (in-points round down, out-points round up so no word is
clipped). Driving Premiere is left to the MCP; this script only does the arithmetic and naming.

With --source-layout (the source sequence's tracks, read from Premiere), every segment also gets
"placements": the matching piece of every camera and mic clip, on the same track, in sync. Audio tracks
other than the consolidated mix (--mix-track, or guessed from track names) are marked muted.

Usage:
  build_premiere_plan.py edl.json --source-sequence "EP12 Multicam" [--fps 25] [--prefix EP12]
                         [--source-layout layout.json] [--mix-track A3]
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


MIX_NAME_HINTS = ("mix", "master", "clean", "final", "consolidated", "enhanced")


def resolve_mix_track(layout, mix_track=None):
    """Index of the consolidated/clean audio track: explicit 'A3' / '3' (1-based) or a name hint, else None."""
    tracks = layout.get("audio_tracks", [])
    if mix_track:
        number = int(str(mix_track).upper().lstrip("A"))
        if not 1 <= number <= len(tracks):
            raise ValueError(f"mix track {mix_track} not in the source (has {len(tracks)} audio tracks)")
        return number - 1
    for pos, track in enumerate(tracks):
        if any(hint in (track.get("name") or "").lower() for hint in MIX_NAME_HINTS):
            return pos
    return None


def mirror_tracks(plan, layout, mix_track=None):
    """Add per-track placements so every cut keeps all cameras and mics as separate, editable clips.

    layout = the source sequence's tracks as read from Premiere (see references/mcp_tool_map.md):
      {"video_tracks": [{"index": 0, "name": "Cam A", "clips": [
           {"name": "...", "start": s, "end": s, "in": s, "out": s, "project_item_id": "...", "media_path": "..."}]}],
       "audio_tracks": [... same shape, optional "channel": 1 ...]}
    start/end are source-sequence seconds; in/out are media seconds. For each segment and each source track,
    the overlapping part of every clip is mapped onto the same track index at the same relative time,
    which keeps multi-camera and multi-mic sync. Audio tracks other than the mix track are muted.
    """
    fps = plan["fps"]
    mix_index = resolve_mix_track(layout, mix_track)
    audio_tracks = layout.get("audio_tracks", [])
    track_info = {
        "video": [{"index": t["index"], "name": t.get("name") or f"V{t['index'] + 1}", "muted": False}
                  for t in layout.get("video_tracks", [])],
        "audio": [{"index": t["index"], "name": t.get("name") or f"A{t['index'] + 1}",
                   "role": "mix" if pos == mix_index else ("iso" if mix_index is not None else "audio"),
                   "muted": mix_index is not None and pos != mix_index}
                  for pos, t in enumerate(audio_tracks)],
        "mix_track": None if mix_index is None else f"A{audio_tracks[mix_index]['index'] + 1}",
    }
    warnings = []

    for seq in plan["sequences"]:
        seq["tracks"] = track_info
        for seg in seq["segments"]:
            a, b = seg["src_in_frame"], seg["src_out_frame"]
            placements = []
            for kind, tracks in (("video", layout.get("video_tracks", [])), ("audio", audio_tracks)):
                for track in tracks:
                    for clip in track.get("clips", []):
                        c0 = snap(clip["start"], fps, "down")
                        c1 = snap(clip["end"], fps, "down")
                        o0, o1 = max(a, c0), min(b, c1)
                        if o1 <= o0:
                            continue
                        media_len = clip["out"] - clip["in"]
                        if abs(media_len - frame_to_seconds(c1 - c0, fps)) > 1.5 / exact_fps(fps):
                            warnings.append(f"{seq['name']}: {kind} track {track['index'] + 1} clip "
                                            f"'{clip.get('name')}' has a speed change; place it by hand")
                            continue
                        media_in = clip["in"] + frame_to_seconds(o0 - c0, fps)
                        media_out = media_in + frame_to_seconds(o1 - o0, fps)
                        p = {"track_type": kind, "track_index": track["index"], "track_name": track.get("name"),
                             "clip_name": clip.get("name"), "project_item_id": clip.get("project_item_id"),
                             "media_path": clip.get("media_path"),
                             "media_in_s": round(media_in, 6), "media_out_s": round(media_out, 6),
                             "media_in_ticks": int(round(media_in * TICKS_PER_SECOND)),
                             "media_out_ticks": int(round(media_out * TICKS_PER_SECOND))}
                        if kind == "audio":
                            p["channel"] = clip.get("channel", 1)
                        p.update(time_fields("timeline_in", seg["timeline_in_frame"] + (o0 - a), fps))
                        p.update(time_fields("timeline_out", seg["timeline_in_frame"] + (o1 - a), fps))
                        placements.append(p)
            if not placements:
                warnings.append(f"{seq['name']}: segment {seg['label']} has no source clips under it")
            seg["placements"] = placements
    plan["warnings"] = plan.get("warnings", []) + warnings
    return plan


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("edl")
    ap.add_argument("--source-sequence", required=True, help="Name of the Premiere sequence holding the full episode")
    ap.add_argument("--fps", type=float, default=None, help="Source sequence frame rate (default: EDL 'fps' or 25)")
    ap.add_argument("--prefix", help="Sequence name prefix (default from episode_title)")
    ap.add_argument("--include-unverified", action="store_true", help="Plan unverified items, named *_UNVERIFIED")
    ap.add_argument("--source-layout", help="Source sequence track layout JSON (enables per-track multicam/multi-mic cuts)")
    ap.add_argument("--mix-track", help="Consolidated/clean mic track, e.g. A3 (default: guessed from track names)")
    ap.add_argument("-o", "--output")
    args = ap.parse_args()

    with open(args.edl, encoding="utf-8") as fh:
        edl = json.load(fh)
    fps = args.fps or edl.get("fps") or 25
    plan = build_plan(edl, args.source_sequence, fps, args.prefix, args.include_unverified)
    if args.source_layout:
        with open(args.source_layout, encoding="utf-8") as fh:
            layout = json.load(fh)
        plan = mirror_tracks(plan, layout, args.mix_track)
        for w in plan["warnings"]:
            print(f"warning: {w}", file=sys.stderr)
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
