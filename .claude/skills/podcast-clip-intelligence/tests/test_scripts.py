"""Synthetic tests for resolve_and_snap.py and rank_candidates.py. Run: python3 -m unittest discover -s tests -v"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))

from resolve_and_snap import resolve_all, snap_candidate  # noqa: E402
from rank_candidates import rank, weighted_score, WEIGHTS  # noqa: E402


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
        self.assertLessEqual(out["end"], 0.0 + 0.5 * 4 + 0.8 + 0.3 + 0.01)


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


if __name__ == "__main__":
    unittest.main()
