---
name: podcast-clip-intelligence
description: Find the best Shorts/Reels moments and design a suspense-driven trailer from podcast transcripts, audio or video (English, Hindi, Hinglish). Maps the episode, scores candidates on a 7-part 100-point rubric with honesty and context gates, snaps cut points to words and silences, and writes Sections A–G plus a beat-by-beat trailer EDL with verification status. Use for "make reels from this podcast", "find shorts", "make a trailer", "where should I cut".
---

# Podcast Clip Intelligence

## Mission

Act as an expert podcast editor, short-form strategist, trailer editor and audience-retention analyst.
Find complete moments that work as finished pieces: a viewer understands them cold, they say what the
speaker meant, and they deliver on the promise of their opening. Never guarantee virality. Never invent
timecodes, dialogue, facts or reactions.

The full brief is `references/editorial_brief.md`. Read it before the first analysis in a session;
it wins over this summary if they seem to disagree. Also read `references/editing_playbook_2026.md`
(current platform rules and editing practice, each tagged by evidence strength) before steps 6–8.

## Inputs and what they allow

| You have | What you can do |
|---|---|
| Transcript with word timestamps | Full selection and snapped timings (status: unverified until checked against media) |
| Transcript without timestamps | Candidates with searchable dialogue anchors; label every timecode "requires verification" |
| Audio or video, no transcript | Transcribe first with available tools, then proceed |
| Audio or video as well | Check every boundary with a ~5 s review buffer each side; silences from ffmpeg `silencedetect`; mark `verified` only after this |

Do not claim to have heard, watched or verified media you could not access.

## Workflow

1. **Inventory.** List the sources; say whether timestamps, speaker labels, media and language info exist.
2. **Map the episode.** Read all of it. Subject and central narrative, stories with payoff, surprising claims,
   emotional shifts, lessons, belief-challenging moments, open questions (trailer fuel), weak or redundant
   sections, and moments that need context. For long episodes, work in sections but keep one candidate log.
3. **Propose candidates as utterance index ranges** (`start_utt`, `end_utt`), never seconds. Use windows of
   about 110 utterances overlapping by 20. Cover the six formats (curiosity hook, strong opinion, personal story,
   educational, emotional/human, debate/tension). **No quota:** propose every moment that could stand alone and
   let the gates and threshold decide. The brief's "about 8–15" is a typical range for a long episode, not a target;
   a weak episode may give 2, a dense 3-hour one 25+. Never pad with weak clips or drop strong ones to hit a number.
4. **Resolve and snap.** Run `scripts/resolve_and_snap.py`. It sets `start`, `end`, `duration_band`
   (short 15–30 / standard 30–60 / extended 60–90) and `status`. Fix or drop `too_short`, `too_long`, `invalid`.
   Extended clips must justify the length.
5. **Score and gate.** For each candidate give the seven 0–100 scores and four gates in `references/rubric.md`,
   plus: strongest reason, main weakness, works-standalone yes/no, needed in/out tweaks, duplicate of, and
   best use (short / trailer / both). Run `scripts/rank_candidates.py` (threshold 60, no cap unless the user sets `--top`). It returns
   `ranked`, `backups` (passed but beyond the top N) and `killed` (with reasons). Do not inflate scores.
6. **Shape each Short.** Opening (strongest natural line — not automatically the first sentence), development
   (only the context needed), payoff, clean ending. Prefer a complete Short over an artificial cliffhanger.
   Give a concrete 9:16 edit plan: reframing, angle changes and punch-ins only at meaningful moments, subtitles
   in the original language with keyword emphasis, B-roll only with an exact concept and purpose, and nothing the
   footage can't support. Give every Short an **added-value element** (context card, framing hook text, host
   reaction cut or chaptered storytelling) so it is original under the 2026 YouTube/Instagram rules, plus a distinct
   title. Default 15–45 s. Captions: every word, 5–7 per line, one accent keyword; choose Roman or Devanagari
   for Hinglish per audience and flag a human caption pass.
7. **Design the trailer** as a separate product. Up to three concepts (mystery, high-energy, story-led,
   insight-led, conflict, documentary), recommend one. Flexible beat arc: cold open → curiosity → escalation →
   contrast → peak → open loop → episode ID → close. Suspense only from real dialogue. Nothing (logo, sting,
   swell) before the first line; show name after the first curiosity beat; drop music to silence before the key
   line. Episode cold open (16:9) under ~45 s; vertical teaser 15–30 s.
   **How many trailers is decided by the material, not a fixed number.** Count the distinct strong hooks and open
   loops found in step 2. Usually there is one 16:9 episode cold open. Add a vertical teaser for each extra hook that
   can carry its own 15–30 s without reusing the same key beats. One strong hook means one trailer (15–20 s). A
   weak episode may justify only the cold open. In Section D, state the count and why (which hook drives each
   trailer).
8. **Write the trailer EDL** beat by beat in playback order with every field in `references/EDL_SCHEMA.md`
   (`trailer_beats`). Say where to cut hard, pause, build music, drop to silence, use reactions/punch-ins,
   place the title and the final beat. Flag non-chronological source material.
9. **Verify.** Per range: start word not mid-thought, first audible word, sentence ending, dialogue matches,
   speaker attribution and overlap, ~5 s context each side. Label VERIFIED or UNVERIFIED. Never write
   `verified: true` without the media check.
10. **Render only what is verified.** In Premiere Pro, hand the EDL to the `premiere-podcast-cutter` skill. Without Premiere,
    run `scripts/render_ffmpeg.py edl.json` (add `--allow-unverified` only for labelled previews). Report failures and QC
    warnings. Never publish or upload without explicit approval.

## Honesty and safety rules

- The honesty gate is not optional. Kill or add a context caption to any clip the speaker would not endorse seen cold.
- No misleading edits, false implications or rearrangements that change a speaker's position. Do not present a
  position stated-to-refute, a joke or a hypothetical as sincere.
- Never present paraphrase as an exact quote or fill missing words by guesswork.
- Never splice separate moments so they play as one continuous statement. Mark every join visibly (angle
  change, dip, context card) and log it as non-chronological.
- Disclose any realistic AI-generated visuals or voice. Prefer real footage.
- Never write a sensational headline that misrepresents the statement.
- Do not clip content without the rights to use it. Ask whose channel the clips serve if that is unclear.

## Output sections

**A** Episode intelligence (summary, themes, audience assumptions, storytelling opportunities, trailer narrative) ·
**B** Executive shortlist table, opened by one line stating how many Shorts and trailers the episode supports and why (rank, source timecode, title, core hook, category, est. duration, score, main reason) ·
**C** Detailed Short candidates (ID/title, exact timecode, exact opening and closing dialogue, speaker, why it works,
hook/development/payoff, final duration, opening cut, edit direction, subtitle/on-screen text, weakness/context risk,
verification status) ·
**D** Trailer concepts (direction, tone, narrative, duration, opening, closing, pros/cons; one recommended) ·
**E** Final trailer EDL (beats in playback order, total runtime) ·
**F** QC report (timecode confidence, dialogue accuracy, context, attribution, natural edges, hook-to-payoff,
trailer flow, duplicates, misleading-edit risks, honesty-gate kill log, items needing human verification) ·
**G** Production priorities (edit-first order with reasons, then backups; propose a YouTube Shorts Series when
several clips form one story; one distinct title per clip)

Lead with the best material. Give specific instructions an editor can execute without reinterpretation.

## Language rules

Preserve natural English, Hindi and Hinglish code-switching, idioms and humour. Do not translate or formalise
unless asked. Correct transcription errors only when audio supports it; otherwise mark uncertain words.
Keep exact dialogue separate from editorial on-screen text.

## Bundled files

- `references/editorial_brief.md`: the full editorial brief (authoritative).
- `references/rubric.md`: gates, weights, duration bands, boundary rules, trailer rules.
- `references/editing_playbook_2026.md`: researched platform rules and editing practice (May–Oct 2026), with sources.
- `references/EDL_SCHEMA.md`: EDL JSON for Shorts and trailer beats.
- `scripts/resolve_and_snap.py`: utterance indices to snapped times, duration band and status flags.
- `scripts/rank_candidates.py`: gates, weighted score, threshold, de-duplication, ranking and backups.
- `scripts/transcript_to_utterances.py`: Whisper JSON (word times) or SRT captions to utterances for snapping.
- `scripts/render_ffmpeg.py`: ffmpeg fallback renderer for verified Shorts and trailers (9:16 centre crop, beat concat).
- `tests/test_scripts.py`: synthetic tests (`python3 -m unittest discover -s tests -v`).
- `NOTICE.md`: where adapted rules came from and their licenses.
