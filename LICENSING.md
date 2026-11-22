# Licensing

| What | Licence |
|---|---|
| Code, tools, `decisions/`, `results/`, docs | MIT (`LICENSE`) |
| `tasks/<board>__*` from edaloop's testbenches (gain_block_demo, four_channel_demo, lband_element, cband_element) | MIT, as edaloop (loopfarmer/edaloop) |
| `tasks/archive-lora__*`, `tasks/archive-qtpy__*` | CC BY-SA 3.0, from Adafruit's designs (see each task's `NOTICE.md`) |
| `tasks/archive-lna915__*`, `tasks/archive-operacake__*` | GPL-2.0, from Great Scott Gadgets' HackRF repository (see each task's `NOTICE.md`) |

The archive tasks are derived works. Each holds a board description written by `edaloop describe` from the released
layout, the board's own footprints exported to `lib/imported.pretty`, and for some tasks one injected fault. Each
task's `NOTICE.md` names the source repository and commit, the licence and what changed. They're shared under the
same licence as their source, as CC BY-SA 3.0 and GPL-2.0 require. The original design files stay in their authors'
repositories: fetch them with `edaloop eval` at the pinned commits.
