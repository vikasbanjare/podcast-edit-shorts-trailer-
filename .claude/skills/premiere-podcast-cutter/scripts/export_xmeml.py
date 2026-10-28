#!/usr/bin/env python3
"""Write a Premiere-importable FCP7 XML (xmeml) from a track-mirrored cut plan.

Input: plan.json from build_premiere_plan.py run with --source-layout (every segment has "placements"
with media_path). Output: one XML holding a bin with one sequence per Short/trailer. Every camera and mic
is its own unlinked clip on its own track, with the original media file, so everything stays editable.
Iso mic tracks are disabled (the mix track plays); re-enable them in Premiere if needed.

Usage: export_xmeml.py plan.json -o cuts.xml [--bin-name "EP12 Cuts"]
Import in Premiere: File > Import > cuts.xml. Relink if the media lives at a different path.
"""
import argparse
import json
import os
import sys
import urllib.parse
import xml.etree.ElementTree as ET

from build_premiere_plan import nominal_fps

NTSC = (23.976, 29.97, 59.94)


def pathurl(path):
    """file://localhost URL for a local path (POSIX or Windows)."""
    p = path.replace("\\", "/")
    if len(p) > 1 and p[1] == ":":  # C:/...
        p = "/" + p
    return "file://localhost" + urllib.parse.quote(p, safe="/")


def _rate(parent, fps):
    rate = ET.SubElement(parent, "rate")
    ET.SubElement(rate, "timebase").text = str(nominal_fps(fps))
    ET.SubElement(rate, "ntsc").text = "TRUE" if any(abs(fps - r) < 0.01 for r in NTSC) else "FALSE"


def _text(parent, tag, value):
    ET.SubElement(parent, tag).text = str(value)
    return parent


class FileRegistry:
    """xmeml defines each media file once, then references it by id."""

    def __init__(self, fps, durations):
        self.fps, self.ids, self.durations = fps, {}, durations

    def element(self, parent, path, has_video, has_audio):
        if path in self.ids:
            ET.SubElement(parent, "file", id=self.ids[path])
            return
        fid = f"file-{len(self.ids) + 1}"
        self.ids[path] = fid
        f = ET.SubElement(parent, "file", id=fid)
        _text(f, "name", os.path.basename(path.replace("\\", "/")))
        _text(f, "pathurl", pathurl(path))
        _rate(f, self.fps)
        _text(f, "duration", self.durations[path])
        media = ET.SubElement(f, "media")
        if has_video:
            ET.SubElement(media, "video")
        if has_audio:
            audio = ET.SubElement(media, "audio")
            _text(audio, "channelcount", 2)


def build_xml(plan, bin_name="Podcast Cuts"):
    fps = plan["fps"]

    def frames(seconds):  # clip in/out are counted at the sequence rate (media assumed to share it)
        return int(round(seconds * exact_rate(fps)))

    # Each file's duration must cover its furthest out-point; real duration is read again on relink.
    durations, kinds = {}, {}
    for seq in plan["sequences"]:
        for seg in seq["segments"]:
            if "placements" not in seg:
                raise ValueError("plan has no placements: run build_premiere_plan.py with --source-layout")
            for p in seg["placements"]:
                if not p.get("media_path"):
                    raise ValueError(f"{seq['name']}: placement on {p['track_type']} {p['track_index'] + 1} has no media_path")
                durations[p["media_path"]] = max(durations.get(p["media_path"], 0), frames(p["media_out_s"]) + 1)
                kinds.setdefault(p["media_path"], set()).add(p["track_type"])
    files = FileRegistry(fps, durations)

    root = ET.Element("xmeml", version="4")
    project = ET.SubElement(root, "project")
    _text(project, "name", bin_name)
    children = ET.SubElement(project, "children")

    clip_no = 0
    for seq in plan["sequences"]:
        s = ET.SubElement(children, "sequence", id=seq["name"])
        _text(s, "name", seq["name"])
        _text(s, "duration", seq["total_frame"])
        _rate(s, fps)
        media = ET.SubElement(s, "media")
        video = ET.SubElement(media, "video")
        fmt = ET.SubElement(ET.SubElement(video, "format"), "samplecharacteristics")
        _rate(fmt, fps)
        _text(fmt, "width", seq["frame"]["width"])
        _text(fmt, "height", seq["frame"]["height"])
        audio = ET.SubElement(media, "audio")

        info = seq.get("tracks", {"video": [], "audio": []})
        n_video = max([t["index"] + 1 for t in info["video"]] + [1])
        n_audio = max([t["index"] + 1 for t in info["audio"]] + [1])
        v_tracks = [ET.SubElement(video, "track") for _ in range(n_video)]
        a_tracks = [ET.SubElement(audio, "track") for _ in range(n_audio)]
        for t in info["audio"]:
            _text(a_tracks[t["index"]], "enabled", "FALSE" if t.get("muted") else "TRUE")

        placements = [p for seg in seq["segments"] for p in seg["placements"]]
        for p in sorted(placements, key=lambda p: p["timeline_in_frame"]):
            clip_no += 1
            track = (v_tracks if p["track_type"] == "video" else a_tracks)[p["track_index"]]
            ci = ET.SubElement(track, "clipitem", id=f"clipitem-{clip_no}")
            _text(ci, "name", p.get("clip_name") or os.path.basename(p["media_path"]))
            _text(ci, "duration", durations[p["media_path"]])
            _rate(ci, fps)
            _text(ci, "start", p["timeline_in_frame"])
            _text(ci, "end", p["timeline_out_frame"])
            media_in = frames(p["media_in_s"])
            _text(ci, "in", media_in)
            _text(ci, "out", media_in + (p["timeline_out_frame"] - p["timeline_in_frame"]))
            files.element(ci, p["media_path"], "video" in kinds[p["media_path"]], "audio" in kinds[p["media_path"]])
            if p["track_type"] == "audio":
                src = ET.SubElement(ci, "sourcetrack")
                _text(src, "mediatype", "audio")
                _text(src, "trackindex", p.get("channel", 1))

        markers = seq.get("markers", [])
        for m in markers:
            mk = ET.SubElement(s, "marker")
            _text(mk, "name", m["name"])
            _text(mk, "comment", m.get("comment", ""))
            _text(mk, "in", round(m["time_s"] * exact_rate(fps)))
            _text(mk, "out", -1)

    ET.indent(root)
    return '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n' + ET.tostring(root, encoding="unicode") + "\n"


def exact_rate(fps):
    return nominal_fps(fps) * (1000 / 1001 if any(abs(fps - r) < 0.01 for r in NTSC) else 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--bin-name", default="Podcast Cuts")
    args = ap.parse_args()
    with open(args.plan, encoding="utf-8") as fh:
        plan = json.load(fh)
    try:
        text = build_xml(plan, args.bin_name)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    with open(args.output, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"wrote {args.output} ({len(plan['sequences'])} sequences)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
