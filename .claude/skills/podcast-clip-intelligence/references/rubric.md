# Tuned clip rubric (v2)

Source material: claude-shorts (weights, boundary rules), clip-factory (honesty gate, arc check),
clip-pipeline-skill (utterance-index method), ClipRank (pacing component), Podcast-Clipper (Q→A
and no-greeting rules), youtube-agent-skill (hook-score caveat). Weights are our tuning, not measured.

## 1. Gates (pass/fail, checked first)

A candidate that fails any gate is killed, whatever its score.

| Gate | Pass when |
|---|---|
| `honesty` | The speaker would say "yes, that's what I meant" seeing the clip cold. Sarcasm, hypotheticals, jokes and positions stated to refute are killed or get a context caption. |
| `arc_complete` | The clip has a setup, a turn and a landing, all inside the clip. A strong line with its setup cut off fails. |
| `standalone_context` | A viewer who hasn't heard the episode understands who is speaking and what "it", "that" and "they" refer to. |
| `no_greeting_or_ad` | No greetings, goodbyes, sponsor reads or thank-yous make up the opening or closing. |

Timing gate (set by `resolve_and_snap.py`): duration 15–60 seconds. Shorts default to 15–30 seconds.
Use 30–60 seconds only when the payoff needs the time.

## 2. Weighted score (0–100 per dimension)

| Dimension | Weight | What a high score looks like |
|---|---|---|
| Hook | 0.25 | The first line creates a question or a bold claim. |
| Standalone | 0.25 | Complete sense without the episode. |
| Emotion / curiosity | 0.15 | Strong opinion, surprise, humour or real feeling. |
| Value density | 0.15 | An actionable insight, number or framework per second. |
| Payoff | 0.10 | The clip ends on the landed point, not a trailing "so yeah". |
| Pacing | 0.10 | Few dead seconds; words per second in a natural range. |

Threshold: 60. Keep the top 8–12 by score. Never add weak clips to reach a target count.

## 2a. Length and ending rules (from jevcut's labelling rubric)

- **Shortest working cut wins.** When two cuts both land, prefer the shorter one. Target band: 25–75 s for
  feed clips. Shorts default to 15–30 s, per section 1.
- **End at the earliest point where the payoff lands.** Stop at the punchline or the answer. Drop restatements,
  "so yeah", a second example of the same point, and the next topic's first line.
- **Open on the first line that grabs.** Skip "so", "okay so next", "let's talk about". But keep any setup
  the payoff needs. A clip that opens on a hook and then loses the viewer is worse than one that starts a sentence earlier.
- **Label tempting negatives.** Keep a list of clips that sound clippable but don't stand alone: narration of a
  screen, a claim whose support came earlier, sponsor reads, intros and sign-offs, inside references.
  Reject these explicitly and log them with the reason.

## 3. Selection procedure

1. Transcribe with word-level timestamps. Keep the utterance index.
2. Build overlapping windows of about 110 utterances with 20 overlapping, so a boundary moment is seen whole.
3. For each window, the LLM proposes candidates as **utterance index ranges only** (`start_utt`, `end_utt`).
   It never writes seconds.
4. `resolve_and_snap.py` maps indices to times and snaps the boundaries.
5. The LLM scores the surviving candidates and runs the gates.
6. `rank_candidates.py` applies the threshold, removes overlapping duplicates, and ranks.
7. Each survivor is checked against audio. Only then does `verified` become true.

## 4. Boundary rules (applied by `resolve_and_snap.py`)

- Start: 0.15 s before the first word, or at the end of a silence that sits just before it.
- End: the last word plus 0.30 s, capped at the start of the next silence.
- If the last word isn't a sentence end, extend up to 3 seconds to the next sentence-ending word.
  Sentence-ending marks: `. ? !` and the Hindi danda `।`.
- Hard limits: 15 s minimum, 60 s maximum. Anything outside is flagged, not silently trimmed.

## 5. Trailer rules

- Length 30–60 seconds; 15–20 seconds if there is only one strong hook.
- Beat order: hook (0–5 s), premise (one specific sentence), one taste of value, close (show name said twice).
- Stop a strong story just before its resolution, so the full episode is worth watching.
  This is an open loop built from real dialogue, never invented drama.
- Music and sound stay below the speech. One stinger at most.
- Trailers must not reorder dialogue in a way that changes the speaker's position. Mark any non-chronological source.

## 6. Language

Keep Hindi, English and Hinglish exactly as spoken. Do not translate or formalise. Mark uncertain words
instead of guessing. Keep on-screen text separate from exact dialogue.
