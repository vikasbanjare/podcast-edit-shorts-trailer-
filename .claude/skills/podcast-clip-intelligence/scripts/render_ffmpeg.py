#!/usr/bin/env python3
"""Render Shorts and trailers from an EDL with ffmpeg (fallback when Premiere is not used).

Reads the EDL described in references/EDL_SCHEMA.md and writes one MP4 per clip and one per trailer.
Only items with "verified": true are rendered unless --allow-unverified is passed, in which case
output files get a "_UNVERIFIED" suffix so they are never mistaken for finals.

- Shorts: cut [start, end] from source_media, optionally centre-cropped and scaled to width x height.
- Trailers: each beat is cut and the beats are concatenated in playback ("sequence") order.
  Beats with a null start/end are skipped and reported.

The EDL may hold a single "trailer" object or a "trailers" list. Use --dry-run to print the
ffmpeg commands without running them. Nothing here uploads or publishes.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

AUDIO_ARGS = ["-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
VIDEO_ARGS = ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p"]


def reframe_filter(width, height):
    """Centre-crop to the target aspect ratio, then scale. Speaker-tracking reframes belong in the NLE."""
    if not width or not height:
        return None
    return (f"crop='min(iw,ih*{width}/{height})':'min(ih,iw*{height}/{width})',"
            f"scale={width}:{height}:flags=lanczos,setsar=1")


def cut_command(source, start, end, out_path, width=None, height=None, subtitle_file=None):
    """ffmpeg command that re-encodes [start, end] so cuts land on the exact frame, not the nearest keyframe."""
    if end is None or start is None or end <= start:
        raise ValueError(f"bad range {start}-{end} for {out_path}")
    filters = [f for f in (reframe_filter(width, height),) if f]
    if subtitle_file:
        filters.append(f"subtitles='{subtitle_file}'")
    cmd = ["ffmpeg", "-hide_banner", "-y", "-ss", f"{start:.3f}", "-i", source, "-t", f"{end - start:.3f}"]
    if filters:
        cmd += ["-vf", ",".join(filters)]
    return cmd + VIDEO_ARGS + AUDIO_ARGS + ["-movflags", "+faststart", out_path]


def concat_command(list_file, out_path):
    return ["ffmpeg", "-hide_banner", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
            "-c", "copy", "-movflags", "+faststart", out_path]


def _safe_name(text):
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in str(text))


def plan(edl, allow_unverified=False):
    """Return (jobs, skipped). Each job is {"id", "kind", "out", "parts": [cut dicts]}."""
    source = edl["source_media"]
    out_dir = edl.get("output_dir", "output")
    jobs, skipped = [], []

    def suffix(item):
        return "" if item.get("verified") is True else "_UNVERIFIED"

    for clip in edl.get("clips", []):
        if clip.get("verified") is not True and not allow_unverified:
            skipped.append((clip["id"], "not verified"))
            continue
        if clip.get("start") is None or clip.get("end") is None:
            skipped.append((clip["id"], "no timecodes (dialogue anchor only)"))
            continue
        sub = clip.get("subtitle_file") if clip.get("burn_subtitles") else None
        jobs.append({
            "id": clip["id"], "kind": "short",
            "out": os.path.join(out_dir, f"{_safe_name(clip['id'])}{suffix(clip)}.mp4"),
            "parts": [{"start": clip["start"], "end": clip["end"], "width": clip.get("width"),
                       "height": clip.get("height"), "subtitle_file": sub}],
        })

    trailers = edl.get("trailers") or ([edl["trailer"]] if edl.get("trailer") else [])
    for i, trailer in enumerate(trailers, 1):
        tid = trailer.get("id") or f"trailer-{i:02d}"
        beats = sorted(trailer.get("beats", []), key=lambda b: b["sequence"])
        unverified = [b["sequence"] for b in beats if b.get("verified") is not True]
        if unverified and not allow_unverified:
            skipped.append((tid, f"unverified beats {unverified}"))
            continue
        parts = []
        for beat in beats:
            if beat.get("start") is None or beat.get("end") is None:
                skipped.append((f"{tid} beat {beat['sequence']}", "no timecodes"))
                continue
            parts.append({"start": beat["start"], "end": beat["end"],
                          "width": trailer.get("width"), "height": trailer.get("height"), "subtitle_file": None})
        if not parts:
            skipped.append((tid, "no renderable beats"))
            continue
        mark = "_UNVERIFIED" if unverified else ""
        jobs.append({"id": tid, "kind": "trailer",
                     "out": os.path.join(out_dir, f"{_safe_name(tid)}{mark}.mp4"), "parts": parts})
    return jobs, skipped


def commands_for(job, source, workdir):
    """List of ffmpeg commands for one job; trailers cut each beat into workdir and then concatenate."""
    if job["kind"] == "short":
        p = job["parts"][0]
        return [cut_command(source, p["start"], p["end"], job["out"], p["width"], p["height"], p["subtitle_file"])]
    cmds, list_lines = [], []
    for n, p in enumerate(job["parts"], 1):
        part_path = os.path.join(workdir, f"{_safe_name(job['id'])}_beat{n:02d}.mp4")
        cmds.append(cut_command(source, p["start"], p["end"], part_path, p["width"], p["height"]))
        list_lines.append(f"file '{part_path}'")
    list_file = os.path.join(workdir, f"{_safe_name(job['id'])}_concat.txt")
    job["concat_list"] = (list_file, "\n".join(list_lines) + "\n")
    cmds.append(concat_command(list_file, job["out"]))
    return cmds


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("edl", help="EDL JSON file")
    ap.add_argument("--allow-unverified", action="store_true",
                    help="Also render unverified items, as *_UNVERIFIED.mp4 previews")
    ap.add_argument("--dry-run", action="store_true", help="Print commands only")
    args = ap.parse_args()

    with open(args.edl, encoding="utf-8") as fh:
        edl = json.load(fh)
    jobs, skipped = plan(edl, allow_unverified=args.allow_unverified)
    for item, reason in skipped:
        print(f"skip {item}: {reason}", file=sys.stderr)
    if not jobs:
        print("nothing to render", file=sys.stderr)
        return 0
    if not args.dry_run and shutil.which("ffmpeg") is None:
        print("ffmpeg not found on PATH", file=sys.stderr)
        return 2

    failures = 0
    with tempfile.TemporaryDirectory(prefix="render_") as workdir:
        for job in jobs:
            os.makedirs(os.path.dirname(job["out"]) or ".", exist_ok=True)
            cmds = commands_for(job, edl["source_media"], workdir)
            if "concat_list" in job and not args.dry_run:
                path, text = job["concat_list"]
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(text)
            for cmd in cmds:
                if args.dry_run:
                    print(" ".join(cmd))
                    continue
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    failures += 1
                    print(f"FAILED {job['id']}: {result.stderr.strip().splitlines()[-1:]}", file=sys.stderr)
                    break
            else:
                if not args.dry_run:
                    print(f"wrote {job['out']}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
