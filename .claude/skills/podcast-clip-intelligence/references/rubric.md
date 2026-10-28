# Clip rubric (v3)

Scoring follows the editorial brief (`editorial_brief.md` section 5). Gates, boundary rules and the
utterance-index method are carried over from v2; see `NOTICE.md` for sources. The score is a
prioritisation tool, not a prediction of views.

## 1. Gates (pass/fail, checked first)

A candidate that fails any gate is killed, whatever its score. Log every kill with its reason (Section F).

| Gate | Pass when |
|---|---|
| `honesty` | The speaker would say "yes, that's what I meant" seeing the clip cold. Sarcasm, hypotheticals, jokes and positions stated to refute are killed or get a context caption. |
| `arc_complete` | The clip delivers the payoff its opening promises, inside the clip. A strong line with its setup cut off fails. |
| `standalone_context` | A viewer who hasn't heard the episode understands who is speaking and what "it", "that" and "they" refer to. |
| `no_greeting_or_ad` | No greetings, goodbyes, sponsor reads or thank-yous make up the opening or closing. |

Timing (set by `resolve_and_snap.py`): 15–90 seconds, in three bands:

| Band | Duration | Use |
|---|---|---|
| `short` | 15–30 s | Default for Shorts/Reels |
| `standard` | 30–60 s | When the payoff needs development |
| `extended` | 60–90 s | Only when the story genuinely needs it; say why |

Content and pacing set the length; the bands are guides, not targets.

## 2. Weighted score

Give each dimension a 0–100 score. The weight is its share of the 100-point total.

| Key | Dimension | Weight (points) |
|---|---|---|
| `hook` | Opening hook and immediate attention | 0.20 (20) |
| `curiosity` | Curiosity, novelty or emotional impact | 0.20 (20) |
| `standalone` | Standalone clarity and context | 0.15 (15) |
| `payoff` | Story progression and payoff | 0.15 (15) |
| `relevance` | Relevance to the target audience | 0.10 (10) |
| `shareability` | Shareability and discussion potential — would someone send it to a specific person? | 0.10 (10) |
| `editing` | Editing feasibility and visual storytelling potential, incl. a clear added-value element | 0.10 (10) |

Threshold: 60. Keep the top 15 at most. Clips that pass but fall outside the top N are returned as
`backups` for Section G. Never add weak clips to reach a target count, and do not inflate scores.

For each candidate also record: strongest reason, main weakness or risk, works without the full episode
(yes/no), needed in-point / opening / ending changes, duplicate of (id or none), best use (short / trailer / both).

## 2a. Length and ending rules

- **Shortest working cut wins.** When two cuts both land, prefer the shorter one.
- **End at the earliest point where the payoff lands.** Drop restatements, "so yeah", a second example of the
  same point, and the next topic's first line.
- **Open on the strongest natural line.** Skip "so", "okay so next", "let's talk about", but keep any setup the
  payoff needs. Opening options: bold statement then explanation; the intriguing question; where the story turns;
  a short reaction or exchange; the result, then how it happened.
- **Never manufacture a hook** by changing the speaker's meaning, and prefer a complete Short over an
  artificial cliffhanger.
- **Label tempting negatives.** Clips that sound clippable but don't stand alone (narration of a screen, a claim
  whose support came earlier, sponsor reads, intros and sign-offs, inside references) are rejected and logged.

## 3. Selection procedure

1. Transcribe with word-level timestamps. Keep the utterance index.
2. Map the whole episode before choosing anything.
3. Build overlapping windows of about 110 utterances with 20 overlapping, so a boundary moment is seen whole.
4. For each window, propose candidates as **utterance index ranges only** (`start_utt`, `end_utt`). Never seconds.
5. `resolve_and_snap.py` maps indices to times, snaps the boundaries and sets the duration band.
6. Score the surviving candidates and run the gates.
7. `rank_candidates.py` applies the threshold, removes overlapping duplicates, ranks, and splits off backups.
8. Each survivor is checked against media. Only then does `verified` become true.

## 4. Boundary rules (applied by `resolve_and_snap.py`)

- Start: 0.15 s before the first word, or at the end of a silence that ends just before it (never after it starts).
- End: the last word plus 0.30 s, capped at the start of the next silence.
- If the last word isn't a sentence end, extend up to 3 seconds to the next sentence-ending word.
  Sentence-ending marks: `. ? !` and the Hindi danda `।`, including when followed by a closing quote or bracket.
- Hard limits: 15 s minimum, 90 s maximum. Anything outside is flagged, not silently trimmed.

## 5. Trailer rules

- A trailer sells the experience of the episode; it doesn't summarise it.
- Length: about 30–60 seconds; 15–20 seconds if there is only one strong hook.
- Flexible arc: cold open → curiosity → escalation → contrast → peak → open loop → episode identification → close.
- Open loops come from real dialogue: stop a strong story before its resolution, never invent drama.
- Music and sound sit below speech. Few effects: no random whooshes, and no transition over an important word.
- Rearranged dialogue must not change a speaker's position. Mark every non-chronological beat, and make every
  join visible so separate moments never play as one statement.
- Nothing before the first line; show name after the first curiosity beat. Cold open under ~45 s; teaser 15–30 s.
- Current practice and its evidence: `editing_playbook_2026.md`.

## 6. Language

Keep Hindi, English and Hinglish exactly as spoken. Do not translate or formalise. Mark uncertain words
instead of guessing. Keep on-screen text separate from exact dialogue.
