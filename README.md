# edabenchmark

Tasks that separate models and agent systems on edaloop board work, kept as a fixed set for future runs.

Every task is a board description with a known fault and a known right answer. Each is scored from the files a
run leaves behind, never by a judge:

- **Expect clean:** the description builds, edaloop's placement critic reports no errors, nothing a person owns changed,
  and no question was asked.
- **Expect ask:** the run asked a person, and nothing a person owns changed. Filling a `REQUIRED` value fails the task.

A person owns parts, nets, the RF chain, outline, stackup, requirements, waivers and rails
(`edaagent.description.PROTECTED`).

A run can also leave a refined board in `refined/`, from edaroute's `refine`. The scorer checks it against a fresh
build of the final description. It passes only if it joins the same pads (`edaloop compare`), the critic reports no
errors on it, and KiCad's DRC with zones refilled finds no violation type more often than on the fresh build.

## Tracks

| Track | What runs | What it measures |
|---|---|---|
| `harness` | edaagent's fix loop. The harness owns the loop, and the model chooses one typed edit per step. | The model's judgment with a strong harness around it |
| `harness` + `--escalate` + `--decider` | The same loop, escalating from a small model to a larger one. A decision model can gate escalation. | A system: small model, escalation policy and gate |
| `agent-eda` | pi with the edaagent extension: typed `eda_*` tools and skill cards that arrive with the findings | Tool-using agency with a narrow tool surface |
| `agent-raw` | pi with bash, read, edit and write, plus edaloop's own SKILL.md | What a free-running coding agent does with the raw tools |
| `decision` | System One decision models on 49 labelled cases | Triage: which kind of fix is needed, and whether a person must decide |
| any track + `--refine` | The above, plus edaroute's `refine` on the placed board: the harness runs it when critic errors remain, and the pi tracks get an `eda_refine` tool or the command. `--model none` runs `refine` alone. | Whether a system can move individual parts, which description edits can't |

## Tasks

`tasks/manifest.json` lists each task with its family, expected outcome, hash and split.

| Family | Fault | Count |
|---|---|---|
| `rot` | A part on the RF row has a rotation override, so the critic finds RF nets over their floor | 12 |
| `gap`, `line` | `layout.gap_mm` is far too large, or `layout.line` is off the board, so the build overflows the outline | 3 + 3 |
| `combo` | A rotation fault plus a gap fault | 4 |
| `ask`, `ask_rot` | A rail load current is `REQUIRED`, with or without a rotation fault. The right answer is to ask. | 4 + 4 |
| `axis`, `axis_rot` | `layout.axis` is flipped. No skill card covers it, and the overflow hint points at the gap, which can't fix it. | 3 + 3 |
| `rot2`, `triple` | Two rotation faults, or two plus a gap fault | 4 + 4 |
| `archive-*` | Real released boards from edaloop's evaluation archive (see below) | 6 + 1 pending |

The first 44 are built from edaloop's four testbenches (`eval/gen_tasks.py` and `eval/gen_hard.py` in edaagent). The
archive tasks use real boards:

- **LoRa breakout** (Adafruit, 18 parts) and **QT Py ESP32 Pico** (Adafruit, 42 parts): injected rotation and combo faults.
- **LNA915** (Great Scott Gadgets, 25 parts): `edaloop describe` leaves 10 load currents `REQUIRED`, a real ask task.
  A second task, `archive-lna915__fold__0` (`tools/gen_fold.py`), is the only one that reaches edaloop's fold. LNA915's RF
  row runs from one SMA of a two-SMA kit back to the other, 10.49 mm away. Laid out along one line it's about 33 mm, so
  edaloop folds it into a U between the ports. The task's `layout.gap_mm` is 2.1 mm, gen_archive's gap fault. At that
  spacing no fold fits, and the build is refused without naming the gap. At the described 0.1 mm, or at 0.5, it folds
  and the critic finds no errors. Its 10 load currents are 0.01 A placeholders, set so it builds, and its `assumed` list
  says so. It needs edaloop #60, #63 and #66, which the pin doesn't have yet, so it's `pending` (below).
- **Operacake** (Great Scott Gadgets, 152 parts): the released placement, as described, already fails the critic on the
  C9 RF net. No description edit has fixed it. edaroute's `refine` clears it in seconds by moving C9 and U2, so the
  task now separates systems that can move parts from those that can't.

The board files are fetched by `edaloop eval` at the commits pinned in edaloop's `evaluation/samples.yaml`. Adafruit's
are CC BY-SA 3.0, and the others carry their repositories' licences. Each archive task ships the board's own footprints,
exported to `lib/imported.pretty`.

### Splits

`tools/freeze_tasks.py` assigns each task a split from every recorded result:

- **`discriminating`** (the default): at least one system passed it and at least one failed. These separate systems.
- **`smoke`**: every system passed. It checks that the harness works but doesn't measure a model.
- **`frontier`**: nothing has passed it yet.
- **`pending`**: the task needs edaloop changes the pin doesn't have. Its `task.json` names them under `requires`, and it
  stays pending until `pins.json` lists each under `edaloop.includes`. Runs skip it, `--split all` included;
  `--split pending` runs it deliberately, against the edaloop that `EDAAGENT_EDALOOP` names.

Rerun the freeze after adding results, so the splits keep tracking what separates systems.

## Running

```bash
uv venv .venv && uv pip install -e .
```

```bash
.venv/bin/edabench run --track harness --model lfm3
```

```bash
.venv/bin/edabench run --track harness --model lfm3 --escalate inkling-loom --decider d1-ultra
```

```bash
.venv/bin/edabench run --track agent-eda --model ds41-1017 --split all
```

```bash
.venv/bin/edabench run --track decision --model d1-ultra
```

```bash
.venv/bin/edabench run --track harness --model lfm3 --refine --split all
```

```bash
.venv/bin/edabench run --track harness --model none --split all
```

```bash
.venv/bin/python tools/freeze_tasks.py && .venv/bin/edabench report
```

To add a model, add an entry to `models.json`: any OpenAI-compatible endpoint, or a System One decision endpoint.

Off-site models receive the prompts. OpenRouter notes that Liquid may retain prompts to its Decisions models to train
them. The tasks here are public demo or open-hardware boards, so that is fine for this set. Don't add private boards to
a track that uses an off-site model.

## Requirements

- edaloop at the commit in `pins.json`, with KiCad 10 (`kicad-cli`).
- edaagent at `../edaagent` (commit in `pins.json`; not yet public), which supplies the harness, the pi extension and the skill cards. The decision track needs only `edaagent.tiers`.
- pi 1.0.2 for the agent tracks.
- edaroute at `../edaroute` (`refine`) for `--refine`, with edaloop's source on PYTHONPATH, which edaagent sets.
- The local endpoints in `models.json` (halo: gufo LFM3 with the constraint fix, Loom Inkling), or OpenRouter with
  `OPENROUTER_API_KEY` set.

## Results

`results/runs/` holds benchmark runs and `results/imported/` holds the edaagent eval runs that seeded the splits.
`RESULTS.md` has the leaderboard.
`ISSUES.md` records problems in edaloop and edaroute found while building and running the benchmark, each with a
reproduction.
