# Edit Decision List (EDL) schema

Use UTF-8 JSON. Source times are seconds from the start of the original source media.
Final-edit times (`final_duration_s`, `final_in_s`) are positions in the finished edit and are kept separate.

```json
{
  "episode_title": "Episode title",
  "source_media": "input/episode.mp4",
  "output_dir": "output",
  "clips": [
    {
      "id": "short-01",
      "title": "Candidate title",
      "type": "short",
      "category": "personal_story",
      "start": 123.4,
      "end": 148.9,
      "duration_band": "short",
      "verified": false,
      "status": "ok",
      "snap_notes": ["end extended to sentence end"],
      "language": "Hinglish",
      "speaker": "Guest",
      "dialogue": "Exact source dialogue",
      "dialogue_anchor": "searchable phrase from the opening line",
      "score": 82.5,
      "aspect_ratio": "9:16",
      "width": 1080,
      "height": 1920,
      "subtitle_file": null,
      "burn_subtitles": false,
      "notes": "Open on the question; cut the restatement after the payoff."
    }
  ],
  "trailer": {
    "concept": "mystery-driven",
    "non_chronological": true,
    "total_runtime_s": 42.0,
    "beats": [
      {
        "sequence": 1,
        "role": "cold_open",
        "start": 812.3,
        "end": 816.1,
        "verified": false,
        "speaker": "Guest",
        "dialogue": "Exact source dialogue",
        "audience_reaction": "Wait, what happened?",
        "purpose": "Open on the stakes without the context",
        "transition": "Hard cut on the last syllable",
        "shot": "Tight on guest, no reframe",
        "audio": "Silence under the line; low drone enters on the cut",
        "on_screen_text": null,
        "final_in_s": 0.0,
        "final_duration_s": 3.8
      }
    ]
  },
  "honesty_log": [
    {"id": "c7", "kill_reasons": ["gate failed: honesty"], "note": "Sarcastic aside; reads sincere out of context."}
  ]
}
```

## Required fields

- `source_media`: path to the source file.
- `clips`: list of clips (may be empty when only a trailer is delivered).
- Each clip: `id`, `start`, `end`.
- Each trailer beat (when `trailer` is present): `sequence`, `start`, `end`, `speaker`, `dialogue`, `final_duration_s`.

## Optional fields

- Clip: `title`, `type`, `category`, `duration_band`, `verified`, `status`, `snap_notes`, `language`, `speaker`,
  `dialogue`, `dialogue_anchor`, `score`, `aspect_ratio`, `width`, `height`, `subtitle_file`, `burn_subtitles`, `notes`.
- Trailer: `concept`, `non_chronological`, `total_runtime_s`.
- Beat: `role` (`cold_open`, `curiosity`, `escalation`, `contrast`, `peak`, `open_loop`, `episode_id`, `close`),
  `verified`, `audience_reaction`, `purpose`, `transition`, `shot`, `audio`, `on_screen_text`, `final_in_s`.
- `honesty_log`: killed candidates with reasons, from `rank_candidates.py`.

## Rules

- `start` and `end` are source-media seconds, never final-timeline positions.
- `end` must be greater than `start`.
- When the source has no reliable timecodes, set `start`/`end` to `null`, fill `dialogue_anchor`, and keep `verified: false`.
- Set `verified: true` only after checking against source media.
- Trailer beats are listed in playback order. Set `non_chronological: true` when any beat comes from earlier in the
  source than the beat before it.
- A renderer does not validate the semantic accuracy of the dialogue or whether the edit is misleading.
- Subtitle files should be SRT or ASS with timestamps relative to the clip, unless the renderer offsets source-timeline captions.
