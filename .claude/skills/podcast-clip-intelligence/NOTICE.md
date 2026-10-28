# Notice and attribution

The rules in this skill were adapted from the following public projects. I read the sections that define
selection rules, weights and boundary handling; I did not audit every file. The code in `scripts/` is newly
written for this skill, based on the ideas below.

| Source | License | What was adapted |
|---|---|---|
| [AgriciDaniel/claude-shorts](https://github.com/AgriciDaniel/claude-shorts) | MIT | Five-dimension weights (hook 0.30 → tuned to 0.25), 15–55 s candidates, sentence-end extension within 3 s, 300 ms padding, 5–60 s limits, post-export checks |
| [mohitagw15856/pm-claude-skills — clip-factory](https://github.com/mohitagw15856/pm-claude-skills) | MIT | Arc-completeness check, honesty gate, "cut to the arc, not the clock", ranked clip sheet with a killed-clips log |
| [wenayy/clip-pipeline-skill](https://github.com/wenayy/clip-pipeline-skill) | MIT | LLM returns utterance indices, not seconds; overlapping windows; resolve indices to times |
| [Squawk7200/ClipRank](https://github.com/Squawk7200/ClipRank) | No license file | Idea of a pacing component and a duration-fit check (no code or text copied) |
| [Ayu270/Podcast-Clipper-Backend](https://github.com/Ayu270/Podcast-Clipper-Backend) | Apache-2.0 | Avoid greetings, ads and unfinished exchanges; Q→A and story clips |
| [Jakeschincariol/youtube-agent-skill](https://github.com/Jakeschincariol/youtube-agent-skill) | MIT | Hook-score caveat: good for weak hooks, not a predictor of hits |
| [RajkumarDake/clipwise](https://github.com/RajkumarDake/clipwise) | MIT | Pause threshold idea (0.35 s) for cut tightening |

Repos without a license file (ClipRank, skill-autoshorts, viral-clip-editor-skill, lexiitong/skillclip, jperrello/shorts)
were studied only for ideas. No text or code from them is included.
