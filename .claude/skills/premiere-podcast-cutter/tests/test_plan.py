"""Tests for build_premiere_plan.py. Run: python3 -m unittest discover -s tests -v"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))

from build_premiere_plan import TICKS_PER_SECOND, build_plan, snap, timecode  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
