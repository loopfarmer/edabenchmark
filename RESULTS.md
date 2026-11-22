# Results

First leaderboard, 2026-11-22. Produced by `edabench report --md` from `results/runs/` (benchmark runs) and
`results/imported/` (the edaagent eval runs that seeded the splits). Splits come from `tools/freeze_tasks.py` over the
same rows, so systems run on more tasks shape the splits more.

A cell like `9/15 of 23` means the system was run on 15 of the 23 tasks in that split and passed 9.

| track | system | discriminating | frontier | smoke | archive | all | med s | $ |
|---|---|---|---|---|---|---|---|---|
| agent-eda | ds41-1017 | 21/23 | 0/0 of 1 | 21/21 of 26 | - | 42/44 | 18 | 0.0000 |
| agent-eda | lfm3 | 9/15 of 23 | 0/0 of 1 | 15/15 of 26 | - | 24/30 | 27 | 0.0000 |
| agent-raw | ds41-1017 | 17/23 | 0/0 of 1 | 21/21 of 26 | - | 38/44 | 71 | 0.0000 |
| agent-raw | lfm3 | 0/11 of 23 | 0/0 of 1 | 0/0 of 26 | - | 0/11 | 600 | 0.0000 |
| harness | ds41-1017 | 7/8 of 23 | 0/1 | 11/11 of 26 | 5/6 | 18/20 | 11 | 0.0177 |
| harness | inkling-loom | 6/8 of 23 | 0/1 | 11/11 of 26 | 5/6 | 17/20 | 40 | 0.0000 |
| harness | lfm3 | 17/23 | 0/1 | 26/26 | 5/6 | 43/50 | 8 | 0.0000 |
| harness | lfm3+esc:ds41-1017 | 6/8 of 23 | 0/0 of 1 | 6/6 of 26 | - | 12/14 | 39 | 0.0038 |
| harness | lfm3+esc:ds41-1017+d1-ultra | 7/8 of 23 | 0/0 of 1 | 6/6 of 26 | - | 13/14 | 24 | 0.0121 |
| harness | lfm3+esc:inkling-loom | 5/8 of 23 | 0/0 of 1 | 6/6 of 26 | - | 11/14 | 41 | 0.0000 |
| harness | lfm3+esc:inkling-loom+d1-ultra | 7/8 of 23 | 0/1 | 11/11 of 26 | 5/6 | 18/20 | 42 | 0.0007 |
| harness | lfm3+noperson | 15/15 of 23 | 0/0 of 1 | 15/15 of 26 | - | 30/30 | 6 | 0.0000 |

decision track (latest run per system):
  d1-local         kind 35/49  person 40/49  median 0.26s  $0.00000
  d1-ultra         kind 48/49  person 49/49  median 0.16s  $0.00107
  gemini-decision  kind 31/49  person 49/49  median 0.25s  $0.00303

## Coverage gaps and notes

- **Inkling 2 Mini under pi** (agent-raw, agent-eda): left out. The first attempt failed on every request, because Loom
  rejects pi's message format until the provider sets `compat` (`supportsDeveloperRole: false` and related; now in
  `models.json` as `pi_compat`). A rerun was in progress at commit time.
- **agent-raw lfm3**: stopped after 11 tasks. Every run hit the 600 s limit (about 89K input tokens), so the remaining
  tasks wouldn't have changed the picture.
- **Prompt overlays** (per-model patches in edaagent `prompts/overlays/`): an A/B was in progress at commit time, and
  isn't in this table.
- **`$`** counts OpenRouter and decision-model spend that the harness tracked. The pi-track OpenRouter spend isn't
  tracked. From the token counts, agent-raw ds41-1017 was about $0.5 for 44 tasks.
- **Frontier:** archive-operacake (152 parts). Nothing has solved it with layout options. DeepSeek V4.1 Flash 1017
  asked a person, which may be the right answer.
