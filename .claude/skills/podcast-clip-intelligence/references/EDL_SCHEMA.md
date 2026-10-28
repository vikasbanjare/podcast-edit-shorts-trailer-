# Edit Decision List (EDL) schema

Use UTF-8 JSON. Times are seconds from the start of the original source media.

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
      "start": 123.4,
      "end": 168.9,
      "verified": true,
      "language": "Hinglish",
      "speaker": "Guest",
      "dialogue": "Exact source dialogue",
      "score": 86,
      "aspect_ratio": "9:16",
      "width": 1080,
      "height": 1920,
      "subtitle_file": null,
      "burn_subtitles": false,
      "notes": "Use a clean opening and preserve the full payoff."
    }
  ]
}
```

## Required fields
- `source_media`: path to the source file.
- `clips`: list of clips.
- Each clip: `id`, `start`, `end`.

## Optional fields
- `title`, `type`, `verified`, `language`, `speaker`, `dialogue`, `score`, `aspect_ratio`, `width`, `height`, `subtitle_file`, `burn_subtitles`, `notes`.

## Rules
- `start` and `end` are source-media seconds, not final-timeline positions.
- `end` must be greater than `start`.
- Set `verified: true` only after checking against source media.
- The renderer does not validate the semantic accuracy of the dialogue or whether the edit is misleading.
- Subtitle files should be SRT or ASS files with timestamps relative to the clip, unless you adapt the renderer to offset source-timeline captions.
