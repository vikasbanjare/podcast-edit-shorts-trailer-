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

## Set up any editing laptop (Mac or Windows)

Run once per laptop (re-run any time to update):

```
# Mac
curl -fsSL https://raw.githubusercontent.com/vikasbanjare/podcast-edit-shorts-trailer-/claude/new-session-sd91hc/setup/setup-mac.sh | bash
# Windows (PowerShell): clone the repo, then
powershell -ExecutionPolicy Bypass -File setup\setup-windows.ps1
```

The setup:
- checks git, Python, Node 20+, Claude Code and ffmpeg;
- clones or updates the skills;
- keeps your existing Premiere MCP, or installs `adobe-premiere-pro-mcp` and registers it with Claude Code;
- runs the tests.

Each editing day:
1. Open Premiere and start `Window > Extensions > MCP Bridge (CEP)`.
2. In the repo folder, run `claude remote-control` (on Mac, `caffeinate -dimsu claude remote-control`, so it doesn't sleep).

The laptop then appears in the Claude app, and a session can be started on whichever laptop is online.

No MCP on a laptop? `premiere-podcast-cutter/scripts/export_xmeml.py` writes an XML you open with File > Import.

## Tests

```
python3 -m unittest discover -s .claude/skills/podcast-clip-intelligence/tests -v
python3 -m unittest discover -s .claude/skills/premiere-podcast-cutter/tests -v
```
