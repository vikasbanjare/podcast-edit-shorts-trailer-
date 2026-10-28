"""Synthetic tests for resolve_and_snap.py and rank_candidates.py. Run: python3 -m unittest discover -s tests -v"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))

from resolve_and_snap import resolve_all, snap_candidate  # noqa: E402
from rank_candidates import rank, weighted_score, WEIGHTS  # noqa: E402
from render_ffmpeg import plan, cut_command, commands_for  # noqa: E402
from transcript_to_utterances import from_srt, from_whisper  # noqa: E402


def words(text, start, step=0.5):
    out, t = [], start
    for w in text.split():
        out.append({"w": w, "s": round(t, 2), "e": round(t + step * 0.8, 2)})
        t += step
    return out


def make_transcript():
    # 0: greeting, 1: question, 2: answer part 1, 3: answer part 2 (ends the thought), 4: tangent
    utts = [
        {"speaker": "Host", "words": words("Welcome back to the show.", 0.0)},
        {"speaker": "Host", "words": words("Why did you quit your job?", 10.0)},
        {"speaker": "Guest", "words": words("Because I saw the numbers were wrong", 14.0)},
        {"speaker": "Guest", "words": words("and nobody else would say it.", 22.0)},
        {"speaker": "Host", "words": words("Okay so what next", 30.0)},
    ]
    return utts


class SnapTests(unittest.TestCase):
    def test_ok_candidate_snaps_to_sentence_end_and_pads(self):
        utts = make_transcript()
        cand = {"id": "c1", "start_utt": 1, "end_utt": 3}
        out = snap_candidate(cand, utts, silences=[])
        # first word of utt 1 starts at 10.0, last word of utt 3 ends at the sentence end
        self.assertAlmostEqual(out["start"], 10.0 - 0.15, places=2)
        self.assertGreater(out["end"], 22.0)
        self.assertIn(out["status"], ("ok", "too_short"))

    def test_start_snaps_to_silence_end_when_close(self):
        utts = make_transcript()
        cand = {"id": "c1", "start_utt": 1, "end_utt": 3}
        out = snap_candidate(cand, utts, silences=[[9.4, 9.9]])
        self.assertAlmostEqual(out["start"], 9.9, places=2)
        self.assertIn("start snapped to silence end", out["snap_notes"])

    def test_end_capped_at_silence_start(self):
        utts = make_transcript()
        cand = {"id": "c1", "start_utt": 1, "end_utt": 3}
        last_end = utts[3]["words"][-1]["e"]
        out = snap_candidate(cand, utts, silences=[[last_end + 0.1, last_end + 1.0]])
        self.assertLess(out["end"], last_end + 0.3)
        self.assertIn("end capped at silence start", out["snap_notes"])

    def test_too_short_is_flagged(self):
        utts = make_transcript()
        out = snap_candidate({"id": "c1", "start_utt": 4, "end_utt": 4}, utts, silences=[])
        self.assertEqual(out["status"], "too_short")

    def test_too_long_is_flagged(self):
        long_utts = [{"speaker": "A", "words": words(" ".join(["word"] * 200), 0.0, step=0.5)}]
        out = snap_candidate({"id": "c1", "start_utt": 0, "end_utt": 0}, long_utts, silences=[])
        self.assertEqual(out["status"], "too_long")

    def test_bad_index_is_reported_not_crashed(self):
        result = resolve_all({"utterances": make_transcript(),
                              "candidates": [{"id": "bad", "start_utt": 3, "end_utt": 99}]})
        self.assertEqual(result["candidates"][0]["status"], "invalid")

    def test_hindi_danda_counts_as_sentence_end(self):
        utts = [{"speaker": "G", "words": words("यह पहला हिस्सा है।", 0.0)},
                {"speaker": "G", "words": words("और यह दूसरा।", 5.0)}]
        out = snap_candidate({"id": "h", "start_utt": 0, "end_utt": 0}, utts, silences=[])
        self.assertNotIn("end extended to sentence end", out["snap_notes"])
        self.assertAlmostEqual(out["end"], utts[0]["words"][-1]["e"] + 0.3, places=2)

    def test_mid_sentence_end_is_extended(self):
        utts = [{"speaker": "G", "words": words("this part has no ending", 0.0)},
                {"speaker": "G", "words": words("until here.", 3.0)}]
        out = snap_candidate({"id": "m", "start_utt": 0, "end_utt": 0}, utts, silences=[])
        self.assertIn("end extended to sentence end", out["snap_notes"])
        self.assertAlmostEqual(out["end"], utts[1]["words"][-1]["e"] + 0.3, places=2)

    def test_sentence_end_inside_closing_quote(self):
        utts = [{"speaker": "G", "words": words('he said "no way."', 0.0)},
                {"speaker": "G", "words": words("next thought.", 2.5)}]
        out = snap_candidate({"id": "q", "start_utt": 0, "end_utt": 0}, utts, silences=[])
        self.assertNotIn("end extended to sentence end", out["snap_notes"])

    def test_start_never_snaps_after_first_word(self):
        utts = make_transcript()
        out = snap_candidate({"id": "c1", "start_utt": 1, "end_utt": 3}, utts, silences=[[9.5, 10.05]])
        self.assertLessEqual(out["start"], utts[1]["words"][0]["s"])

    def test_duration_bands(self):
        def band(seconds):
            n = int(seconds / 0.5)
            utts = [{"speaker": "A", "words": words(" ".join(["w"] * (n - 1) + ["end."]), 0.0)}]
            return snap_candidate({"id": "b", "start_utt": 0, "end_utt": 0}, utts, silences=[])
        self.assertEqual(band(20)["duration_band"], "short")
        self.assertEqual(band(45)["duration_band"], "standard")
        extended = band(80)
        self.assertEqual(extended["duration_band"], "extended")
        self.assertEqual(extended["status"], "ok")


class RankTests(unittest.TestCase):
    def scores(self, v):
        return {k: v for k in WEIGHTS}

    def gates(self, ok=True):
        return {"honesty": ok, "arc_complete": ok, "standalone_context": ok, "no_greeting_or_ad": ok}

    def test_weights_sum_to_one(self):
        self.assertAlmostEqual(sum(WEIGHTS.values()), 1.0)

    def test_weighted_score(self):
        self.assertEqual(weighted_score(self.scores(80)), 80.0)

    def test_missing_score_raises(self):
        with self.assertRaises(ValueError):
            weighted_score({"hook": 50})

    def test_gate_failure_kills_even_with_high_score(self):
        cand = {"id": "x", "start": 0, "end": 30, "status": "ok",
                "scores": self.scores(95), "gates": self.gates(ok=True)}
        cand["gates"]["honesty"] = False
        res = rank([cand])
        self.assertEqual(res["ranked"], [])
        self.assertIn("gate failed: honesty", res["killed"][0]["kill_reasons"])

    def test_threshold_kills_low_scores(self):
        cand = {"id": "x", "start": 0, "end": 30, "status": "ok",
                "scores": self.scores(50), "gates": self.gates()}
        res = rank([cand], threshold=60)
        self.assertEqual(res["ranked"], [])

    def test_overlapping_duplicate_is_removed_keeping_higher(self):
        hi = {"id": "hi", "start": 100, "end": 140, "status": "ok", "scores": self.scores(90), "gates": self.gates()}
        lo = {"id": "lo", "start": 110, "end": 150, "status": "ok", "scores": self.scores(70), "gates": self.gates()}
        res = rank([lo, hi])
        self.assertEqual([c["id"] for c in res["ranked"]], ["hi"])
        self.assertTrue(any("overlaps hi" in r for c in res["killed"] for r in c["kill_reasons"]))

    def test_ranking_order_and_top_n(self):
        cands = []
        for i, val in enumerate([70, 90, 80]):
            cands.append({"id": f"c{i}", "start": i * 1000, "end": i * 1000 + 40, "status": "ok",
                          "scores": self.scores(val), "gates": self.gates()})
        res = rank(cands, top_n=2)
        self.assertEqual([c["id"] for c in res["ranked"]], ["c1", "c2"])
        self.assertEqual([c["id"] for c in res["backups"]], ["c0"])
        self.assertEqual(res["killed"], [])

    def test_no_quota_by_default(self):
        cands = [{"id": f"c{i}", "start": i * 100, "end": i * 100 + 30, "status": "ok",
                  "scores": self.scores(70), "gates": self.gates()} for i in range(20)]
        res = rank(cands)
        self.assertEqual(len(res["ranked"]), 20)
        self.assertEqual(res["backups"], [])

    def test_weights_match_brief_points(self):
        points = {k: round(v * 100) for k, v in WEIGHTS.items()}
        self.assertEqual(points, {"hook": 20, "curiosity": 20, "standalone": 15, "payoff": 15,
                                  "relevance": 10, "shareability": 10, "editing": 10})

    def test_candidate_without_timecodes_is_ranked(self):
        cand = {"id": "anchor", "start": None, "end": None, "scores": self.scores(75), "gates": self.gates()}
        other = {"id": "timed", "start": 0, "end": 30, "status": "ok", "scores": self.scores(80), "gates": self.gates()}
        res = rank([cand, other])
        self.assertEqual([c["id"] for c in res["ranked"]], ["timed", "anchor"])


class RenderPlanTests(unittest.TestCase):
    def edl(self):
        return {"source_media": "src.mp4", "output_dir": "out", "clips": [
            {"id": "ok", "start": 1, "end": 20, "verified": True},
            {"id": "unv", "start": 1, "end": 20, "verified": False},
            {"id": "anchor", "start": None, "end": None, "verified": True}],
            "trailer": {"beats": [
                {"sequence": 2, "start": 50, "end": 53, "verified": True},
                {"sequence": 1, "start": 10, "end": 14, "verified": True}]}}

    def test_only_verified_items_render(self):
        jobs, skipped = plan(self.edl())
        self.assertEqual([j["id"] for j in jobs], ["ok", "trailer-01"])
        self.assertEqual(dict(skipped)["unv"], "not verified")
        self.assertIn("anchor", dict(skipped))

    def test_unverified_preview_is_labelled(self):
        jobs, _ = plan(self.edl(), allow_unverified=True)
        self.assertTrue(next(j for j in jobs if j["id"] == "unv")["out"].endswith("_UNVERIFIED.mp4"))

    def test_trailer_beats_follow_playback_order(self):
        jobs, _ = plan(self.edl())
        trailer = next(j for j in jobs if j["kind"] == "trailer")
        self.assertEqual([p["start"] for p in trailer["parts"]], [10, 50])
        cmds = commands_for(trailer, "src.mp4", "/tmp/w")
        self.assertEqual(len(cmds), 3)
        self.assertIn("concat", cmds[-1])

    def test_unverified_beat_blocks_trailer(self):
        edl = self.edl()
        edl["trailer"]["beats"][0]["verified"] = False
        jobs, skipped = plan(edl)
        self.assertNotIn("trailer-01", [j["id"] for j in jobs])

    def test_cut_command_reframes_and_rejects_bad_range(self):
        cmd = cut_command("src.mp4", 2.0, 5.5, "o.mp4", 1080, 1920)
        self.assertEqual(cmd[cmd.index("-t") + 1], "3.500")
        self.assertIn("scale=1080:1920", cmd[cmd.index("-vf") + 1])
        with self.assertRaises(ValueError):
            cut_command("src.mp4", 5, 5, "o.mp4")


class TranscriptTests(unittest.TestCase):
    SRT = ("1\n00:00:10,000 --> 00:00:12,000\nHost: Aapne job kyun chhodi?\n\n"
           "2\n00:00:12,500 --> 00:00:16,500\nGuest: Kyunki numbers galat the.\n\n"
           "3\n00:00:16,500 --> 00:00:18,000\naur koi bol nahi raha tha.\n")

    def test_srt_speakers_and_even_words(self):
        res = from_srt(self.SRT)
        self.assertTrue(res["approximate_words"])
        self.assertEqual([u["speaker"] for u in res["utterances"]], ["Host", "Guest", "Guest"])
        first = res["utterances"][0]["words"]
        self.assertEqual([w["w"] for w in first], ["Aapne", "job", "kyun", "chhodi?"])
        self.assertEqual((first[0]["s"], first[-1]["e"]), (10.0, 12.0))

    def test_srt_offset_and_snap_pipeline(self):
        res = from_srt(self.SRT, offset=100.0)
        out = snap_candidate({"id": "x", "start_utt": 0, "end_utt": 1}, res["utterances"], silences=[])
        self.assertAlmostEqual(out["start"], 110.0 - 0.15, places=2)

    def test_whisper_word_times_kept(self):
        data = {"segments": [{"start": 1.0, "end": 2.0, "text": " Hello there.", "speaker": "SPEAKER_00",
                              "words": [{"word": " Hello", "start": 1.0, "end": 1.4},
                                        {"word": " there.", "start": 1.5, "end": 1.9}]},
                             {"start": 3.0, "end": 4.0, "text": " no words here"}]}
        res = from_whisper(data)
        self.assertEqual(res["utterances"][0]["words"][1], {"w": "there.", "s": 1.5, "e": 1.9})
        self.assertEqual(res["utterances"][0]["speaker"], "SPEAKER_00")
        self.assertTrue(res["approximate_words"])  # second segment had no word times


if __name__ == "__main__":
    unittest.main()
