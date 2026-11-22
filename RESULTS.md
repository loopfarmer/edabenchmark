# Results

Leaderboard as of 2026-11-22. Produced by `edabench report --md` from `results/runs/` (benchmark runs) and
`results/imported/` (the edaagent eval runs that seeded the splits). Splits come from `tools/freeze_tasks.py` over the
same rows, so systems run on more tasks shape the splits more.

A cell like `21/27 of 43` means the system was run on 27 of the 43 tasks in that split and passed 21.

| track | system | discriminating | frontier | smoke | archive | all | med s | $ |
|---|---|---|---|---|---|---|---|---|
| agent-eda | ds41-1017 | 37/39 of 43 | 0/0 | 5/5 of 7 | - | 42/44 | 18 | 0.0000 |
| agent-eda | ds41-1017+refine | 4/4 of 43 | 0/0 | 2/2 of 7 | 6/6 | 6/6 | 14 | 0.0000 |
| agent-eda | lfm3 | 21/27 of 43 | 0/0 | 3/3 of 7 | - | 24/30 | 27 | 0.0000 |
| agent-raw | ds41-1017 | 33/39 of 43 | 0/0 | 5/5 of 7 | - | 38/44 | 71 | 0.0000 |
| agent-raw | lfm3 | 0/11 of 43 | 0/0 | 0/0 of 7 | - | 0/11 | 600 | 0.0000 |
| harness | ds41-1017 | 14/16 of 43 | 0/0 | 4/4 of 7 | 5/6 | 18/20 | 11 | 0.0177 |
| harness | ds41-1017+refine | 42/43 | 0/0 | 7/7 | 5/6 | 49/50 | 9 | 0.0222 |
| harness | inkling-loom | 13/16 of 43 | 0/0 | 4/4 of 7 | 5/6 | 17/20 | 40 | 0.0000 |
| harness | lfm3 | 36/43 | 0/0 | 7/7 | 5/6 | 43/50 | 8 | 0.0000 |
| harness | lfm3+esc:ds41-1017 | 10/12 of 43 | 0/0 | 2/2 of 7 | - | 12/14 | 39 | 0.0038 |
| harness | lfm3+esc:ds41-1017+d1-ultra | 11/12 of 43 | 0/0 | 2/2 of 7 | - | 13/14 | 24 | 0.0121 |
| harness | lfm3+esc:inkling-loom | 9/12 of 43 | 0/0 | 2/2 of 7 | - | 11/14 | 41 | 0.0000 |
| harness | lfm3+esc:inkling-loom+d1-ultra | 14/16 of 43 | 0/0 | 4/4 of 7 | 5/6 | 18/20 | 42 | 0.0007 |
| harness | lfm3+noperson | 27/27 of 43 | 0/0 | 3/3 of 7 | - | 30/30 | 6 | 0.0000 |
| harness | lfm3+refine | 37/43 | 0/0 | 7/7 | 6/6 | 44/50 | 50 | 0.0000 |
| harness | refine-only | 9/43 | 0/0 | 7/7 | 3/6 | 16/50 | 5 | 0.0000 |

decision track (latest run per system):
  d1-local         kind 35/49  person 40/49  median 0.26s  $0.00000
  d1-ultra         kind 48/49  person 49/49  median 0.16s  $0.00107
  gemini-decision  kind 31/49  person 49/49  median 0.25s  $0.00303

## edaroute refine (`+refine`, `refine-only`)

- **`refine-only`** runs no model: it builds the description and runs edaroute's `refine` on the placed board. It
  passes 16/50, mostly rotation faults: it moves parts around a mis-rotated part instead of undoing the rotation, and
  the critic accepts that. It can't fix a board that doesn't build, so overflow, axis and ask tasks fail.
- **Operacake is no longer a frontier task.** `refine` clears its C9 RF error by moving C9 and U2. That's 2 s on its
  own, or after the model's steps in `lfm3+refine` and `ds41-1017+refine` (agent-eda, through the `eda_refine` tool).
- **`ds41-1017+refine` scores 49/50.** Its one miss is operacake, where DeepSeek asked a person before the harness
  reached `refine`. The harness doesn't run `refine` after a question.
- **The DRC guard matters.** On `archive-lora__rot__0`, `refine-only` produced a board the critic accepts but with one
  more `shorting_items` DRC violation than the fresh build. It failed for that reason.

## Coverage gaps and notes

- **Inkling 2 Mini under pi** (agent-raw, agent-eda): left out. The first attempt failed on every request, because Loom
  rejects pi's message format until the provider sets `compat` (now in `models.json` as `pi_compat`). The rerun wasn't
  in at the time of this table.
- **agent-raw lfm3**: stopped after 11 tasks. Every run hit the 600 s limit.
- **Prompt overlays** (per-model patches in edaagent `prompts/overlays/`): the A/B isn't in this table yet.
- **`$`** counts OpenRouter and decision-model spend that the harness tracked. The pi-track OpenRouter spend isn't
  tracked. From the token counts, agent-raw ds41-1017 was about $0.5 for 44 tasks.
- **edaloop tree:** every run used edaloop `8f53d6f` with an uncommitted local debug patch, a copy of `kicad_ops.py`
  that prints `BOX`/`SPAN`/`NOTPLACED` lines to stderr (see `pins.json`). It changes no placement, critic or DRC
  result, only build output.
