# Issues found while building and running edabenchmark

Problems in edaloop and edaroute found on 2026-11-22. Each was reproduced, and each has a command or the file that
shows it. Pins: edaloop 8f53d6f, KiCad 10.0.5. Where edaagent works around an issue, that's noted, so a fix upstream
can retire the workaround.

## edaloop

### E1. A failed build prints debug output, and its reason line comes out garbled

```bash
edaloop build tasks/gain_block_demo__gap__0/description.yaml -o /tmp/ov
```

- **Leftover debug prints.** The build prints 15 `BOX <ref> x0 y0 x1 y1` lines and a `SPAN (...)` line before the real
  reason.
- **Garbled reason line.** The first line reads `edaloop: placement failed: .14`.
- **wx noise.** On other failures KiCad's Python adds `assert "traits" failed in Get(): create wxApp before calling
  this` to the reason.
- **Effect.** An agent reading the output takes the noise for the error.
- **Workaround.** edaagent filters these lines (`eda._NOISE`), which is fragile.

### E2. A failed build leaves a partial folder, and the next build into it refuses

After E1, the output folder holds `board_description.yaml`, `chains_*.yaml` and `edaloop.kicad_sym`. The next `edaloop
build ... -o /tmp/ov` refuses: "isn't empty. Build into a new folder, so that no routed board is overwritten".

- **Why it's wrong.** The refusal protects routed boards, but this folder holds no board.
- **Effect.** It traps agents that rebuild into the same folder after each edit, which is the obvious loop. The
  benchmark's raw-agent prompt said the build replaces the folder, which is false because of this. It likely cost the
  pi-raw runs turns.
- **Suggestion.** Write into a temporary folder and move it into place only on success, or allow overwriting a folder
  that has no `.kicad_pcb`.

### E3. Eagle-imported boards crash `build` with a traceback

```bash
edaloop describe <eval-work>/lora/lora.kicad_pcb -o d.yaml --band-mhz 868 915
```

```bash
edaloop build d.yaml -o b
```

- **Crash.** `ValueError: not enough values to unpack` at `kicad_ops.py:122` (`lib, name = fpid.split(":", 1)`).
- **Cause.** `describe` copies Eagle footprint names (`TSSOP16`, `0805-NO`) with no `library:` prefix.
- **What `build` should do.** Refuse with the refs and names it can't resolve.
- **What `describe` should do.** Offer the regenerate recipe itself: export the board's footprints to
  `imported.pretty`, prefix every footprint, and set `unlisted_pads: open`. That recipe lives only inside
  `evaluate.regenerate`.
- **Workaround.** `tools/gen_archive.py` does this by hand.

### E4. `describe` can't handle boards with many connectors

LibreVNA (4 connectors) and LimeRFE (7) fail with "more routes between the N connectors than can be searched … needs
its chains written by hand". These are the archive's richest RF boards, so the benchmark has no tasks from them.
Accepting a partial chain (the routes found within a budget), or a hint file of connector pairs, would bring them in.

### E5. `edaloop eval --level describe` doesn't keep the description it wrote

The scorecard reports `describe.rf_path`, but the description it was judged on isn't saved in the output folder, so it
has to be regenerated with `edaloop describe` (which needs the band, which the eval already knows).

### E6. Rebuilding a released board from its description doesn't reproduce it

The released operacake ships, but its description rebuilt by `edaloop build` fails the critic:
`placement:rf:Net-(C9-Pad2):over_floor`, 31% over the floor. edaroute's `refine` then clears it in 2 s by moving C9 and
U2.

- **Placer gap.** The placer has a placement this hop can't take. `regen` in `edaloop eval` would show it as a layout
  gap.
- **Description gap.** A description can't move one part, because there is no per-part offset or position. So a
  description-only agent can never fix this. The benchmark keeps the task to separate systems that can move parts
  from those that can't.
- **Suggestion.** Add an optional `layout.place: {REF: [dx, dy]}` override, or run `refine` inside `build`.

### E7. Critic RF findings name the net, not the parts

`placement:rf:LNA1IN:over_floor` says which net is long but not which part causes it, and the fix is always a part
(rotate or move it). Agents have to map net → parts themselves. edaagent does it in `state.focus_parts` and shows the model those parts;
how much LFM3 relies on that hasn't been measured without it. Putting the parts on the net, and any that have a
rotation override, in the finding's message or metrics would save every consumer the mapping.

### E8. Outline-overflow errors are prose only

"parts span x 0.90..69.24, y 4.32..14.49, outside the 40 x 20 mm outline with a 0.5 mm margin" is what an agent must act
on. edaagent regex-parses it (`state._SPAN`) to work out how far, and which way, to move. Those numbers, added together with partial credit for a smaller overflow and refusing repeated edits, took LFM3
from 2/3 to 3/3 on both the gap and line tasks. A `--json` build result with the span, the outline, the margin and the
axis would remove the regex.

### E9. A flipped `layout.axis` isn't diagnosed

With `axis: y` on a board whose long side is x, the build reports only an overflow. The hint the numbers suggest
(shrink `gap_mm`) can't fix it. LFM3 failed all 3 `axis` tasks in the harness; Inkling and DeepSeek V4.1 Flash solved
them. The error could say "the RF row is N mm long; the board is W mm along x and H mm along y".

## edaroute

### R1. `refine` leaves zone fills stale

The moved parts sit inside the GND pour that was filled before the move. KiCad's DRC then reports 10 clearance and 8
solder-mask-bridge violations that disappear with `--refill-zones`. Anyone checking a refined board without refilling
sees errors that aren't there. Anyone who doesn't refill ships a board whose copper overlaps.
Refill the zones in the output, or strip them and say so.
edaagent's `refine.drc_counts` always refills before comparing.

### R2. `refine` needs edaloop on PYTHONPATH and fails with a raw traceback without it

```bash
edaroute refine board.kicad_pcb chains.yaml out.kicad_pcb
```

This ends in `ModuleNotFoundError: No module named 'edaloop'` from `edaloop.scripts.kicad_pcb`.
edaloop isn't a declared dependency. Declaring it, or an `--edaloop PATH` option with a clear error, would fix this.
edaagent sets PYTHONPATH (`refine.refine`).

### R3. `*.refine.json` doesn't record the moves

`docs/refine.md` says the report holds "the start and end costs and metrics, and every move it kept". The file has
`start_cost, cost, start, metrics, moved, kept, seconds` and no list of moves, so a refined board can't be audited
or replayed without diffing the boards. The log line `pass 1: C9: cost 20.4 -> 19.4` names the part, but not the move.

### R4. `refine` takes the chain file as an argument even when it sits beside the board

`edaloop build` writes `chains_<name>.yaml` next to the `.kicad_pcb`, and refine could default to it.

## Elsewhere in the stack (not edaloop or edaroute)

- **gufo LFM3 extension + DSpark:** schema-constrained requests failed with `500 invalid token accepted by JSON
  constraint`. Fixed in the extension's `runner.cpp`, uncommitted in `~/cc/lfm3-gufo-extension`. Constrained requests
  now run one at a time.
- **AMD Loom:** it rejects pi's messages until the provider sets `compat` (`supportsDeveloperRole: false` and related),
  and it ignores `response_format`.
- **pi:** with stdout redirected and stdin open, pi waits on stdin, so runs need `stdin=/dev/null`.
