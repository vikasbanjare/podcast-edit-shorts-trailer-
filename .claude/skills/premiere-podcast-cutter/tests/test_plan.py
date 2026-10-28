"""Tests for build_premiere_plan.py. Run: python3 -m unittest discover -s tests -v"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))

from build_premiere_plan import TICKS_PER_SECOND, build_plan, mirror_tracks, snap, timecode  # noqa: E402
from export_xmeml import build_xml, pathurl  # noqa: E402
import xml.etree.ElementTree as ET  # noqa: E402


def edl():
    return {
        "episode_title": "EP12 Founder Story",
        "source_media": "ep12.mp4",
        "clips": [
            {"id": "short-01", "title": "Why I quit!", "start": 10.01, "end": 30.49, "verified": True,
             "upload_title": "He quit after seeing this", "added_value": "context card"},
            {"id": "short-02", "title": "Draft", "start": 40, "end": 60, "verified": False},
            {"id": "short-03", "title": "Anchor only", "start": None, "end": None, "verified": True},
        ],
        "trailers": [
            {"id": "cold-open", "concept": "mystery", "width": 1920, "height": 1080, "beats": [
                {"sequence": 2, "role": "curiosity", "start": 100.0, "end": 103.0, "verified": True},
                {"sequence": 1, "role": "cold_open", "start": 500.0, "end": 504.0, "verified": True}]},
            {"id": "teaser", "beats": [{"sequence": 1, "start": 5, "end": None, "verified": True}]},
        ],
    }


class PlanTests(unittest.TestCase):
    def test_frame_snapping_never_clips_words(self):
        self.assertEqual(snap(10.01, 25, "down"), 250)
        self.assertEqual(snap(30.49, 25, "up"), 763)
        self.assertEqual(snap(4.0, 25, "up"), 100)  # already on a frame: unchanged

    def test_timecode_and_ticks(self):
        self.assertEqual(timecode(25 * 3661 + 7, 25), "01:01:01:07")
        plan = build_plan(edl(), "EP12 Multicam", 25)
        seg = plan["sequences"][0]["segments"][0]
        self.assertEqual(seg["src_in_ticks"], 10 * TICKS_PER_SECOND)
        self.assertEqual(seg["src_in_tc"], "00:00:10:00")
        self.assertEqual(seg["timeline_in_s"], 0)

    def test_names_verification_and_skips(self):
        plan = build_plan(edl(), "EP12 Multicam", 25)
        names = [s["name"] for s in plan["sequences"]]
        self.assertEqual(names, ["EP12FOUNDERS_SHORT_01_why-i-quit", "EP12FOUNDERS_TRAILER_01_mystery"])
        reasons = {s["id"]: s["reason"] for s in plan["skipped"]}
        self.assertEqual(reasons["short-02"], "not verified")
        self.assertIn("dialogue anchor", reasons["short-03"])
        self.assertIn("without timecodes", reasons["teaser"])
        self.assertEqual(plan["sequences"][0]["upload_title"], "He quit after seeing this")

    def test_unverified_items_are_labelled_when_included(self):
        plan = build_plan(edl(), "src", 25, prefix="ep12", include_unverified=True)
        self.assertIn("EP12_SHORT_02_draft_UNVERIFIED", [s["name"] for s in plan["sequences"]])

    def test_trailer_beats_laid_end_to_end_in_playback_order(self):
        plan = build_plan(edl(), "src", 25)
        trailer = next(s for s in plan["sequences"] if s["kind"] == "trailer")
        segs = trailer["segments"]
        self.assertEqual([s["src_in_s"] for s in segs], [500.0, 100.0])
        self.assertEqual(segs[1]["timeline_in_frame"], segs[0]["timeline_out_frame"])
        self.assertEqual(trailer["total_s"], 7.0)
        self.assertTrue(trailer["non_chronological"])
        self.assertEqual(trailer["frame"], {"width": 1920, "height": 1080})
        self.assertEqual(trailer["markers"][0]["name"], "beat 1 cold_open")

    def test_ntsc_rate(self):
        plan = build_plan({"clips": [{"id": "a", "start": 1.0, "end": 20.0, "verified": True}]}, "src", 29.97)
        seg = plan["sequences"][0]["segments"][0]
        self.assertEqual(seg["src_in_frame"], 29)  # 1.0 s * 29.97 = 29.97 -> rounds down
        self.assertLessEqual(seg["src_in_s"], 1.0)

    def test_duplicate_names_made_unique(self):
        data = {"clips": [{"id": "a", "title": "Same", "start": 0, "end": 20, "verified": True},
                          {"id": "b", "title": "Same", "start": 30, "end": 50, "verified": True}]}
        data["clips"][1]["type"] = "short"
        plan = build_plan(data, "src", 25, prefix="X")
        self.assertEqual(len({s["name"] for s in plan["sequences"]}), 2)


def podcast_layout():
    """Two cameras (Cam A split into two files at 300 s), two iso mics and a consolidated mix."""
    def clip(name, start, end, media_in, path):
        return {"name": name, "start": start, "end": end, "in": media_in, "out": media_in + (end - start),
                "project_item_id": name, "media_path": path}
    return {
        "video_tracks": [
            {"index": 0, "name": "Cam A", "clips": [clip("camA-1", 0, 300, 2.0, "/m/camA_1.mp4"),
                                                    clip("camA-2", 300, 3600, 0.0, "/m/camA_2.mp4")]},
            {"index": 1, "name": "Cam B", "clips": [clip("camB", 0, 3600, 5.0, "/m/camB.mp4")]}],
        "audio_tracks": [
            {"index": 0, "name": "Host mic", "clips": [clip("host", 0, 3600, 1.0, "/m/host.wav")]},
            {"index": 1, "name": "Guest mic", "clips": [clip("guest", 0, 3600, 1.0, "/m/guest.wav")]},
            {"index": 2, "name": "Mix clean", "clips": [clip("mix", 0, 3600, 0.0, "/m/mix.wav")]}],
    }


def multicam_edl():
    return {"clips": [{"id": "s1", "title": "Spans the camera split", "start": 290.0, "end": 310.0, "verified": True}],
            "trailer": {"id": "t", "beats": [
                {"sequence": 1, "start": 1000.0, "end": 1004.0, "verified": True},
                {"sequence": 2, "start": 200.0, "end": 203.0, "verified": True}]}}


class MultitrackTests(unittest.TestCase):
    def plan(self, mix=None):
        return mirror_tracks(build_plan(multicam_edl(), "EP Multicam", 25, prefix="EP"), podcast_layout(), mix)

    def test_every_camera_and_mic_is_placed(self):
        seg = self.plan()["sequences"][0]["segments"][0]
        kinds = sorted((p["track_type"], p["track_index"]) for p in seg["placements"])
        # Cam A appears twice (crosses its file split); Cam B once; three audio tracks.
        self.assertEqual(kinds, [("audio", 0), ("audio", 1), ("audio", 2),
                                 ("video", 0), ("video", 0), ("video", 1)])

    def test_sync_offsets_and_file_split(self):
        seg = self.plan()["sequences"][0]["segments"][0]
        cam_a = sorted((p for p in seg["placements"] if p["clip_name"].startswith("camA")),
                       key=lambda p: p["timeline_in_s"])
        self.assertEqual(cam_a[0]["media_in_s"], 292.0)       # 290 s on the timeline + 2 s offset
        self.assertEqual(cam_a[0]["timeline_out_s"], 10.0)    # file ends at 300 s on the source timeline
        self.assertEqual(cam_a[1]["media_in_s"], 0.0)
        self.assertEqual(cam_a[1]["timeline_in_s"], 10.0)
        cam_b = next(p for p in seg["placements"] if p["clip_name"] == "camB")
        self.assertEqual(cam_b["media_in_s"], 295.0)
        self.assertEqual(cam_b["timeline_out_s"], 20.0)

    def test_mix_track_found_by_name_and_isos_muted(self):
        tracks = self.plan()["sequences"][0]["tracks"]
        self.assertEqual(tracks["mix_track"], "A3")
        self.assertEqual([t["muted"] for t in tracks["audio"]], [True, True, False])

    def test_explicit_mix_track(self):
        tracks = self.plan(mix="A1")["sequences"][0]["tracks"]
        self.assertEqual([t["muted"] for t in tracks["audio"]], [False, True, True])
        with self.assertRaises(ValueError):
            self.plan(mix="A9")

    def test_trailer_beats_keep_all_tracks_in_sync(self):
        trailer = self.plan()["sequences"][1]
        second = trailer["segments"][1]
        self.assertTrue(all(p["timeline_in_s"] == 4.0 for p in second["placements"]))
        self.assertEqual(len(second["placements"]), 5)

    def test_speed_changed_clip_is_flagged_not_placed(self):
        layout = podcast_layout()
        layout["video_tracks"][1]["clips"][0]["out"] = 1800.0  # 2x speed
        plan = mirror_tracks(build_plan(multicam_edl(), "src", 25), layout)
        self.assertTrue(any("speed change" in w for w in plan["warnings"]))

    def test_xml_is_editable_multitrack(self):
        root = ET.fromstring(build_xml(self.plan()).split("\n", 2)[2])
        seqs = root.findall("./project/children/sequence")
        self.assertEqual(len(seqs), 2)
        short = seqs[0]
        self.assertEqual(short.findtext("duration"), "500")
        self.assertEqual(len(short.findall("./media/video/track")), 2)
        audio_tracks = short.findall("./media/audio/track")
        self.assertEqual([t.findtext("enabled") for t in audio_tracks], ["FALSE", "FALSE", "TRUE"])
        first = short.find("./media/video/track/clipitem")
        self.assertEqual((first.findtext("start"), first.findtext("end"), first.findtext("in")), ("0", "250", "7300"))
        defined = [f for f in root.iter("file") if f.find("pathurl") is not None]
        self.assertEqual(len(defined), len({f.findtext("pathurl") for f in defined}))  # each file defined once
        self.assertEqual(short.find("./media/audio/track/clipitem/sourcetrack/trackindex").text, "1")

    def test_xml_requires_layout(self):
        with self.assertRaises(ValueError):
            build_xml(build_plan(multicam_edl(), "src", 25))

    def test_windows_pathurl(self):
        self.assertEqual(pathurl("C:\\Pod cast\\cam A.mp4"), "file://localhost/C%3A/Pod%20cast/cam%20A.mp4")


if __name__ == "__main__":
    unittest.main()
