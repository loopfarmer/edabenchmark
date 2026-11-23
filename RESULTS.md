# Results

Leaderboard as of 2026-11-22. Produced by `edabench report --md` from `results/runs/` (benchmark runs) and
`results/imported/` (the edaagent eval runs that seeded the splits). Splits come from `tools/freeze_tasks.py` over the
same rows, so systems run on more tasks shape the splits more.

A cell like `21/27 of 43` means the system was run on 27 of the 43 tasks in that split and passed 21.

| track | system | discriminating | frontier | smoke | archive | all | med s | $ |
|---|---|---|---|---|---|---|---|---|
| agent-eda | ds41-1017 | 38/41 of 45 | 0/0 | 3/3 of 5 | - | 41/44 | 12 | 0.0000 |
| agent-eda | ds41-1017+overlay | 41/41 of 45 | 0/0 | 3/3 of 5 | - | 44/44 | 11 | 0.0000 |
| agent-eda | ds41-1017+refine | 4/4 of 45 | 0/0 | 2/2 of 5 | 6/6 | 6/6 | 14 | 0.0000 |
| agent-eda | inkling-loom | 40/41 of 45 | 0/0 | 3/3 of 5 | - | 43/44 | 52 | 0.0000 |
| agent-eda | lfm3 | 21/41 of 45 | 0/0 | 3/3 of 5 | - | 24/44 | 92 | 0.0000 |
| agent-eda | lfm3+overlay | 22/41 of 45 | 0/0 | 3/3 of 5 | - | 25/44 | 240 | 0.0000 |
| agent-raw | ds41-1017 | 35/41 of 45 | 0/0 | 3/3 of 5 | - | 38/44 | 71 | 0.0000 |
| agent-raw | ds41-1017+overlay | 36/41 of 45 | 0/0 | 3/3 of 5 | - | 39/44 | 36 | 0.0000 |
| agent-raw | inkling-loom | 26/41 of 45 | 0/0 | 3/3 of 5 | - | 29/44 | 414 | 0.0000 |
| agent-raw | inkling-loom+overlay | 35/45 | 0/0 | 4/5 | 2/6 | 39/50 | 312 | 0.0000 |
| agent-raw | lfm3 | 0/11 of 45 | 0/0 | 0/0 of 5 | - | 0/11 | 600 | 0.0000 |
| harness | ds41-1017 | 16/18 of 45 | 0/0 | 2/2 of 5 | 5/6 | 18/20 | 11 | 0.0177 |
| harness | ds41-1017+refine | 44/45 | 0/0 | 5/5 | 5/6 | 49/50 | 9 | 0.0222 |
| harness | inkling-loom | 43/45 | 0/0 | 5/5 | 5/6 | 48/50 | 20 | 0.0000 |
| harness | inkling-loom+refine | 42/45 | 0/0 | 5/5 | 5/6 | 47/50 | 20 | 0.0000 |
| harness | lfm3 | 38/45 | 0/0 | 5/5 | 5/6 | 43/50 | 15 | 0.0000 |
| harness | lfm3+esc:ds41-1017 | 12/14 of 45 | 0/0 | 0/0 of 5 | - | 12/14 | 39 | 0.0038 |
| harness | lfm3+esc:ds41-1017+d1-ultra | 13/14 of 45 | 0/0 | 0/0 of 5 | - | 13/14 | 24 | 0.0121 |
| harness | lfm3+esc:inkling-loom | 11/14 of 45 | 0/0 | 0/0 of 5 | - | 11/14 | 41 | 0.0000 |
| harness | lfm3+esc:inkling-loom+d1-ultra | 16/18 of 45 | 0/0 | 2/2 of 5 | 5/6 | 18/20 | 42 | 0.0007 |
| harness | lfm3+noperson | 27/27 of 45 | 0/0 | 3/3 of 5 | - | 30/30 | 6 | 0.0000 |
| harness | lfm3+overlay | 35/41 of 45 | 0/0 | 3/3 of 5 | - | 38/44 | 32 | 0.0000 |
| harness | lfm3+refine | 39/45 | 0/0 | 5/5 | 6/6 | 44/50 | 50 | 0.0000 |
| harness | refine-only | 11/45 | 0/0 | 5/5 | 3/6 | 16/50 | 5 | 0.0000 |

decision track (latest run per system):
  d1-local         kind 35/49  person 40/49  median 0.26s  $0.00000
  d1-ultra         kind 48/49  person 49/49  median 0.16s  $0.00107
  gemini-decision  kind 31/49  person 49/49  median 0.25s  $0.00303

## Per-model prompt overlays (`+overlay`)

Overlays are short prompt patches for one model's observed blind spots (edaagent `prompts/overlays/<model>.<surface>.md`),
A/B-tested on all 44 testbench tasks in one run (edaagent eval `r4`).

| System | Without | With overlay | What the patch targeted |
|---|---|---|---|
| agent-eda ds41-1017 | 41/44 | **44/44** | never tried `layout.axis`; left out the `key` argument |
| agent-raw ds41-1017 | 38/44 (earlier run) | 39/44, and tokens per task fell from about 56K to 23K | read source and tried to reproduce the placer, using 100+ calls |
| harness lfm3 | 36/44 | 38/44 | axis flips (still 0/3) |
| agent-eda lfm3 | 24/44 | 25/44 | asking a person instead of choosing a value, ignoring the measured value, repeating dead ends |

- **DeepSeek:** a clear gain. With the tools, the patch fixed the axis tasks it failed. With raw tools, it removed most
  of the exploration.
- **LFM3:** no gain beyond noise. One task here is a single run, and the same unpatched LFM3 system scored `rot2` 2/4 in
  one run and 4/4 in another, so differences of one or two tasks aren't significant.
- **Schema regression for LFM3.** Before this A/B the `eda_change` tool was changed to make `key` required, which fixed
  DeepSeek's missing argument. LFM3 under agent-eda then fell on gap and line, from 3/3 and 1/3 to 0/3 each. The
  agent-eda rows here all use the new schema. A per-model schema was then tried (edaagent eval `r5`): with `key`
  optional, LFM3 scored 21/44, against 22/44 with it required, and gap and line stayed at 0/3 and 1/3. The schema
  wasn't the cause, so `key` stays required for every model. The `pi_tool_schema` setting in `models.json` remains for
  future use.

## Inkling 2 Mini under pi

Rerun with Loom's `compat` settings:
- **agent-eda:** 43/44.
- **agent-raw:** 29/44, mostly 600 s timeouts. Four of its failures filled a `REQUIRED` load current instead of asking
  a person, which the protected-field check scores as a failure.
- **agent-raw with its overlay:** 39/50 on all 50 tasks, and 37/44 on the 44 testbench tasks the plain run used.
  The 17 cband and lband tasks were rerun, because the first run had edaloop's source made read-only (see the
  notes), which left the agent unable to delete its own board folder.

## Inkling 2 Mini in the harness

All 50 tasks, on Loom:

| System | Pass | Misses |
|---|---|---|
| `inkling-loom` | 48/50 | operacake (asked a person), `gain_block_demo__axis__0` (2 critic errors) |
| `inkling-loom+refine` | 47/50 | operacake (asked a person), `cband_element__axis_rot__0`, `gain_block_demo__axis_rot__0` |

`+refine` didn't make boards worse. The two runs missed different tasks. On the two it alone missed, `refine`'s move was
refused because it added silkscreen DRC violations (21 to 24, and 14 to 15), so the model's board was scored as it
stood. The difference is run-to-run noise.

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

- **Inkling 2 Mini under pi:** the first attempt failed on every request, before Loom's `compat` settings were added.
  Those rows are excluded, and the rerun is above.
- **agent-raw lfm3**: stopped after 11 tasks. Every run hit the 600 s limit.
- **Run-to-run variance:** every row is a single run per task. Treat differences of one or two tasks as noise.
- **`$`** counts OpenRouter and decision-model spend that the harness tracked. The pi-track OpenRouter spend isn't
  tracked. From the token counts, agent-raw ds41-1017 was about $0.5 for 44 tasks.
- **edaloop tree:** every run used edaloop `8f53d6f`. The DeepSeek agent-raw runs edited the local clone through
  bash while they ran. They added a debug copy of `kicad_ops.py` and pointed `boardgen.py` at it. The copies only
  printed output, so no placement, critic or DRC result changed. The clone has been reverted (see `pins.json`).
- **Tool-tree check:** since then every agent run records `git status` and `git diff` of the edaloop and edaroute trees
  before and after. A run during which either changed is marked `invalid` and left out of this table. No run has been
  marked invalid yet.
- **Report order:** the table once let older imported seed rows override newer benchmark runs of the same task. With
  that fixed, `harness lfm3` reads 43/50 (was 41/50) and `harness inkling-loom` 48/50.
