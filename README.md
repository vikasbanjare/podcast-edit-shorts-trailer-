# podcast-edit-shorts-trailer

Two Claude Code skills for turning podcast episodes (English, Hindi, Hinglish) into Shorts/Reels and trailers.
Claude Code loads them automatically when this repository is open.

## 1. `podcast-clip-intelligence`: pick the moments

[`.claude/skills/podcast-clip-intelligence/`](.claude/skills/podcast-clip-intelligence/SKILL.md)

- `SKILL.md`: workflow, honesty rules and output sections A–G
- `references/editorial_brief.md`: the full editorial brief the skill follows
- `references/editing_playbook_2026.md`: researched platform rules and editing practice (May–Oct 2026), with sources
- `references/rubric.md`, `references/EDL_SCHEMA.md`: 100-point rubric and the Shorts + trailers EDL format
- `scripts/resolve_and_snap.py`: maps utterance-index candidates to snapped source times
- `scripts/rank_candidates.py`: gates, weighted scoring, de-duplication, ranking and backups
- `scripts/render_ffmpeg.py`: ffmpeg fallback renderer for verified Shorts and trailers

## 2. `premiere-podcast-cutter`: cut them in Premiere Pro

[`.claude/skills/premiere-podcast-cutter/`](.claude/skills/premiere-podcast-cutter/SKILL.md)

Give it the EDL and the name of your source sequence. It drives your Premiere Pro MCP server to create one
named sequence per Short and per trailer. Every camera and mic stays a separate, editable clip on its own track,
in sync: cameras stacked, the consolidated mix live, individual mics muted as backups. It adds beat markers
and reframes to 9:16. It reads every cut back to check it, and exports only when you approve.
It can also write an editable FCP7 XML you import into Premiere directly (File > Import).

- `scripts/build_premiere_plan.py`: EDL plus source track layout to a per-track, frame-accurate cut plan
- `scripts/export_xmeml.py`: cut plan to an importable, editable multitrack XML
- `examples/layout.example.json`: two cameras, two iso mics and a consolidated mix
- `references/mcp_tool_map.md`: tool names for the known community Premiere MCP servers, plus an ExtendScript fallback

## Tests

```
python3 -m unittest discover -s .claude/skills/podcast-clip-intelligence/tests -v
python3 -m unittest discover -s .claude/skills/premiere-podcast-cutter/tests -v
```
