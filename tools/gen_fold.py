"""Build the fold task: LNA915, whose RF row only fits between its two SMAs folded into a U.

  EDAAGENT_EDALOOP=<edaloop with the fold>/.venv/bin/edaloop EDAAGENT_EDALOOP_REPO=<that tree> \\
      python tools/gen_fold.py            (needs the board fetched: `edaloop eval lna915 --level describe -o work/archive`)

LNA915's RF path leaves P1, a two-SMA kit, and comes back to it 10.49 mm away. Laid out along one line the row is about
33 mm, so the placer folds it into a U between the ports (loopfarmer/edaloop#66). No other task reaches that code.

The description is written as gen_archive.py writes one, by `edaloop describe` and the board's own footprints, but with an
edaloop that has the fold. Its footprint export splits P1's courtyard at the gap between the SMAs (edaloop#63); the older
export in archive-lna915__ask_real__0 draws one box over both, which leaves no room between the ports. `describe` measures
`layout.gap_mm` 0.10 from the board (edaloop#67).

`describe` leaves the ten VCC load currents REQUIRED, and a build needs numbers. They're set here to PLACEHOLDER_A each, a
placeholder rather than the board's real draw, and the description's `assumed` list says so. Nothing in the task turns on
them: rails are a person's, so a run that changes them fails anyway.

The fault is gen_archive's gap fault, gap_mm = min(6 * 0.10 + 1.5, 3.0) = 2.1. At 2.1 mm no fold fits, and the build is
refused without naming the gap. At 0.1 or 0.5 mm the row folds and the critic finds no errors; at 1.0 mm it's refused.

The task only counts on an edaloop pin that includes the PRs in REQUIRES; tools/freeze_tasks.py marks it `pending` until
pins.json lists them under edaloop.includes. On the 2026-11-23 pin (8f53d6f) every build of it, the right answer included,
stops at the drawn-schematic check that edaloop#60 fixes.
"""
from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
from edaagent import config, description as dsc, state as stt  # noqa: E402

BOARD = ROOT / "work/archive/lna915"
WORK = BOARD / "fold"
TASK = "archive-lna915__fold__0"
PLACEHOLDER_A = 0.01
GAP_FAULT = 2.1
# The edaloop PRs the task needs, besides those already in the pin: #60 (the loop-through schematic) and #66 (the fold,
# stacked on #63's loop-through placement and footprint export).
REQUIRES = ["loopfarmer/edaloop#60", "loopfarmer/edaloop#63", "loopfarmer/edaloop#66"]
LICENCE = "GPL-2.0 (the repository's licence; the board folder has none of its own)"


def prepare() -> Path:
    pcb = BOARD / "lna915.kicad_pcb"
    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True)
    subprocess.run([config.EDALOOP, "describe", pcb, "-o", WORK / "described.yaml", "--band-mhz", "902", "928"],
                   check=True, capture_output=True)
    kicad_python = subprocess.run([config.EDALOOP_REPO / ".venv/bin/python", "-c",
                                   "from edaloop import toolchain; print(toolchain.paths()['kicad_python'])"],
                                  capture_output=True, text=True, check=True).stdout.strip()
    r = subprocess.run([kicad_python, config.EDALOOP_REPO / "src/edaloop/kicad_ops.py", "export_footprints", pcb,
                        WORK / "lib/imported.pretty"], capture_output=True, text=True, timeout=300)
    report = json.loads(r.stdout.strip().splitlines()[-1])
    if "SMA-KIT-1.5MF" not in report.get("courtyards_split", []):
        raise SystemExit(f"this edaloop's export doesn't split P1's courtyard (needs edaloop#63): {report}")
    d = dsc.load(WORK / "described.yaml")
    d["layout"]["footprints"] = {r: "imported:" + str(fp).split(":")[-1] for r, fp in d["layout"]["footprints"].items()}
    d["layout"]["unlisted_pads"] = "open"
    loads = []
    for rail in d["project"]["rails"]:
        loads += [f"{rail['net']} at {pad}" for pad, v in rail["loads"].items() if v == "REQUIRED"]
        rail["loads"] = {pad: (PLACEHOLDER_A if v == "REQUIRED" else v) for pad, v in rail["loads"].items()}
    d.setdefault("assumed", []).append(
        f"project.rails: the {len(loads)} load currents describe left REQUIRED ({', '.join(loads)}) are {PLACEHOLDER_A} A each, "
        "placeholders set by edabenchmark so the board builds, not the board's real draw")
    dsc.save(d, WORK / "description.yaml")
    return WORK


def evaluate(desc: dict, lib: Path, tmp: Path) -> stt.State:
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    shutil.copytree(lib, tmp / "lib")
    dsc.save(desc, tmp / "description.yaml")
    return stt.evaluate(tmp / "description.yaml", tmp / "b")


def main():
    base = prepare()
    lib = base / "lib"
    good = dsc.load(base / "description.yaml")
    tmp = ROOT / "work/.gen-fold"
    st0 = evaluate(good, lib, tmp / "base")
    if not st0.clean:
        raise SystemExit(f"the described board doesn't build clean, so the task has no known answer: {st0.brief()}")
    bad = copy.deepcopy(good)
    g0 = bad["layout"]["gap_mm"]
    bad["layout"]["gap_mm"] = GAP_FAULT
    # describe's note of the spacing it measured would name the answer, which no other gap task's description does.
    bad["assumed"] = [x for x in bad.get("assumed", []) if not str(x).startswith("layout: gap_mm")]
    st = evaluate(bad, lib, tmp / "fault")
    if st.built or "no fold" not in (st.build_error or ""):
        raise SystemExit(f"the fault doesn't stop the build at the fold: {st.brief()}")
    d = ROOT / "tasks" / TASK
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    dsc.save(bad, d / "description.yaml")
    shutil.copytree(lib, d / "lib")
    t = {"id": TASK, "board": "archive-lna915", "family": "fold", "faults": [f"layout.gap_mm={GAP_FAULT} (was {g0})"],
         "expect": "clean", "source": "edaloop evaluation archive", "licence": LICENCE, "parts": len(bad.get("parts", {})),
         "requires": {"edaloop": REQUIRES}, "initial": st.brief()}
    (d / "task.json").write_text(json.dumps(t, indent=1))
    (d / "NOTICE.md").write_text(f"""# Source and licence

- Board: LNA915 amplifier, by Great Scott Gadgets
- Source: https://github.com/greatscottgadgets/hackrf at commit 468c5d93b66032c892c95bbf9ff15ff1b803e84f, file `hardware/LNA915/LNA915.kicad_pcb`
- Licence: {LICENCE}, https://www.gnu.org/licenses/old-licenses/gpl-2.0.html
- Derived here: `description.yaml` written by `edaloop describe` from the released layout, with footprints rewritten to
  `imported:<name>`; `lib/imported.pretty` exported from the released board. Changes: the
  {sum(len(r['loads']) for r in good['project']['rails'])} VCC load currents are {PLACEHOLDER_A} A placeholders, not the board's draw, and `layout.gap_mm` is {GAP_FAULT} (described as {g0}).
- This derived task is shared under the same licence.
""")
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"{TASK}: {t['faults']} -> {(st.build_error or '')[:120]}")
    print(f"  answer: gap_mm {g0} builds clean, cost {st0.brief().get('cost')}")


if __name__ == "__main__":
    sys.exit(main())
