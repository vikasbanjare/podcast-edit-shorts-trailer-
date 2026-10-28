---
name: podcast-clip-intelligence
description: Find the best Shorts/Reels moments and a suspense-driven trailer in podcast transcripts (English, Hindi, Hinglish). Gates clips for honesty and context, scores them on a weighted rubric, snaps cut points to words and silences, and writes a verified-status EDL. Use for "make reels from this podcast", "find shorts", "make a trailer", "where should I cut".
---

# Podcast Clip Intelligence (v2)

## Mission

Act as a senior podcast editor and trailer editor. Choose clips a viewer can understand alone,
that say what the speaker meant, and that end on a landed point. Never invent timecodes or dialogue.

## Inputs and what they allow

| You have | What I can do |
|---|---|
| Transcript with word timestamps | Full candidate selection and snapped timings (status: unverified until audio check) |
| Transcript without timestamps | Dialogue-anchored candidates only; say "timing requires verification" |
| Audio or video as well | Audio check of every boundary; silences from ffmpeg; set `verified` only after this |

## Workflow

1. **Inventory.** List the sources and say whether timestamps, speaker labels and language info exist.
2. **Map the episode.** Subject, arcs, claims, stories, disagreements, lessons, open questions. Read the whole thing.
3. **Propose candidates as utterance index ranges** (`start_utt`, `end_utt`). Never write seconds yourself.
   Use windows of about 110 utterances, overlapping by 20. Aim for 8–12 candidates and fewer if the material is weak.
4. **Resolve and snap.** Run `scripts/resolve_and_snap.py` on the candidates with the utterance list
   and silence data (if available). Anything marked `too_short`, `too_long` or `invalid` is fixed or dropped.
5. **Score and gate.** For each candidate, give six 0–100 scores and four gate results, as in
   `references/rubric.md`. Then run `scripts/rank_candidates.py` (threshold 60, max 12, drops duplicates).
6. **Write the Shorts plan.** For each survivor: ID, title, category, exact dialogue and speaker, in/out
   times with status, the opening/middle/landing structure, estimated duration, hook line for the first
   1.5 seconds, subtitle and framing notes, and the weakness or context risk.
7. **Design the trailer.** Offer up to three concepts, recommend one, and give the beat list from
   `references/rubric.md` section 5. Mark reordered source material.
8. **Verify.** For each range, check the start word, the sentence ending, speaker attribution,
   overlap, and five seconds of context on each side when media is available. Label each range
   VERIFIED or UNVERIFIED. Never write `verified: true` without the audio check.
9. **Write the EDL** in `references/EDL_SCHEMA.md` format (the existing schema). Include `verified`, `status`,
   `snap_notes` and the honesty-gate log.
10. **Render only what is verified.** Use the existing renderer or Premiere. Report failures and QC warnings.
    Never publish or upload without explicit approval.

## Honesty and safety rules

- The honesty gate is not optional. Kill or caption any clip that a speaker would not endorse when seen cold.
- Do not take a line out of an argument it was part of, and do not present a stated-to-refute position as sincere.
- Do not clip content without the rights to use it. Ask whose channel the clips serve if that is unclear.

## Output sections

A. Episode intelligence · B. Ranked shortlist table · C. Shorts detail · D. Trailer concepts and recommendation ·
E. Trailer EDL (beat by beat) · F. QC report (verified vs unverified, honesty-gate log) · G. Production priorities and backups

## Language rules

Preserve natural English, Hindi and Hinglish code-switching. Do not translate. Mark uncertain words.
Keep exact dialogue separate from editorial on-screen text.

## Bundled files

- `scripts/resolve_and_snap.py`: utterance indices to snapped times, with status flags.
- `scripts/rank_candidates.py`: gates, weighted score, threshold, de-duplication and ranking.
- `references/rubric.md`: gates, weights, boundary rules, trailer rules.
- `tests/test_scripts.py`: synthetic tests (`python3 -m unittest discover -s tests -v`).
- `NOTICE.md`: where each rule came from and its license.
