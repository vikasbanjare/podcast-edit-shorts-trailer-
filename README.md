# podcast-edit-shorts-trailer

Claude Code skill for picking Shorts/Reels clips and a trailer from podcast transcripts
(English, Hindi, Hinglish).

The skill lives in [`.claude/skills/podcast-clip-intelligence/`](.claude/skills/podcast-clip-intelligence/SKILL.md),
so Claude Code loads it automatically when this repository is open.

- `SKILL.md`: workflow, honesty rules and output sections
- `references/`: scoring rubric and EDL schema
- `scripts/resolve_and_snap.py`: maps utterance-index candidates to snapped source times
- `scripts/rank_candidates.py`: gates, weighted scoring, de-duplication and ranking
- `tests/`: run with `python3 -m unittest discover -s .claude/skills/podcast-clip-intelligence/tests -v`
- `NOTICE.md`: sources and licenses of the adapted rules
