"""Build tasks from edaloop's open-hardware archive (edaloop/evaluation/samples.yaml), on real released boards.

  python tools/gen_archive.py            (needs the boards fetched: `edaloop eval <names> --level describe -o work/archive`)

For each board: `edaloop describe` writes a description from the released layout, its own footprints are exported to
lib/imported.pretty (edaloop's regenerate recipe), and the description points at them. Then:
  boards that build clean -> injected faults, as for the testbenches (rot, gap, line, axis, combo): expect clean
  boards whose description has REQUIRED values -> ask_real: expect ask
  boards whose released placement already fails the critic -> frontier: expect clean, solvability unknown
Real boards are larger (18 to 152 parts), so the prompt a model sees is too.
"""
from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
from edaagent import config, description as dsc, state as stt  # noqa: E402

ARCHIVE = ROOT / "work/archive"
BOARDS = {"lora": (868, 915), "qtpy": (2400, 2500), "lna915": (902, 928), "operacake": (1, 6000)}
LICENCE = {"lora": "CC BY-SA 3.0 (Adafruit)", "qtpy": "CC BY-SA 3.0 (Adafruit)",
           "lna915": "see the HackRF repository licence (Great Scott Gadgets)",
           "operacake": "see the HackRF repository licence (Great Scott Gadgets)"}


def prepare(board: str) -> Path:
    """description.yaml + lib/ for one archive board, in work/archive/<board>/base."""
    src = ARCHIVE / board
    pcb = next(src.glob("*.kicad_pcb"))
    base = src / "base"
    if (base / "description.yaml").exists():
        return base
    base.mkdir(parents=True, exist_ok=True)
    lo, hi = BOARDS[board]
    subprocess.run([config.EDALOOP, "describe", pcb, "-o", base / "described.yaml", "--band-mhz", str(lo), str(hi)],
                   check=True, capture_output=True)
    kicad_python = subprocess.run([config.EDALOOP_REPO / ".venv/bin/python", "-c",
                                   "from edaloop import toolchain; print(toolchain.paths()['kicad_python'])"],
                                  capture_output=True, text=True, check=True).stdout.strip()
    ops = config.EDALOOP_REPO / "src/edaloop/kicad_ops.py"
    subprocess.run([kicad_python, ops, "export_footprints", pcb, base / "lib/imported.pretty"],
                   capture_output=True, timeout=300)
    d = yaml.safe_load((base / "described.yaml").read_text())
    d["layout"]["footprints"] = {r: "imported:" + str(fp).split(":")[-1] for r, fp in d["layout"]["footprints"].items()}
    d["layout"]["unlisted_pads"] = "open"
    dsc.save(d, base / "description.yaml")
    return base


def evaluate(desc: dict, lib: Path, tmp: Path) -> stt.State:
    tmp.mkdir(parents=True, exist_ok=True)
    if not (tmp / "lib").exists():
        shutil.copytree(lib, tmp / "lib")
    dsc.save(desc, tmp / "description.yaml")
    return stt.evaluate(tmp / "description.yaml", tmp / "b")


def chain_parts(desc):
    out = []
    for row in desc.get("chain") or []:
        for pad in row[1:3]:
            r = str(pad).split(".")[0]
            if r not in out and not r[:1] in ("J", "X", "P"):
                out.append(r)
    return out


def main():
    out = ROOT / "tasks"
    made = []
    tmp = ROOT / "work/.gen-archive"
    shutil.rmtree(tmp, ignore_errors=True)

    def emit(board, family, desc, faults, expect, st, lib):
        tid = f"archive-{board}__{family}__{sum(1 for m in made if m['board'] == board and m['family'] == family)}"
        d = out / tid
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir(parents=True)
        dsc.save(desc, d / "description.yaml")
        shutil.copytree(lib, d / "lib")
        t = {"id": tid, "board": f"archive-{board}", "family": family, "faults": faults, "expect": expect,
             "source": "edaloop evaluation archive", "licence": LICENCE[board], "parts": len(desc.get("parts", {})),
             "initial": st.brief()}
        (d / "task.json").write_text(json.dumps(t, indent=1))
        made.append(t)
        print(f"  {tid}: {faults} -> {'built, errors ' + str(len(st.errors)) if st.built else (st.build_error or '')[:80]}")

    for board in BOARDS:
        base = prepare(board)
        lib = base / "lib"
        desc0 = dsc.load(base / "description.yaml")
        st0 = evaluate(desc0, lib, tmp / f"{board}_base")
        print(f"## {board}: {len(desc0['parts'])} parts, base {'clean' if st0.clean else st0.brief()}")
        if st0.needs_value:
            emit(board, "ask_real", desc0, ["REQUIRED values from edaloop describe"], "ask", st0, lib)
            continue
        if not st0.clean:
            emit(board, "frontier", desc0, ["the released placement, as described"], "clean", st0, lib)
            continue
        lay = desc0.get("layout") or {}
        rots = []
        for r in chain_parts(desc0):
            for deg in (90, 180):
                if len(rots) >= 2:
                    break
                d = copy.deepcopy(desc0)
                d["layout"].setdefault("rotation", {})[r] = deg
                st = evaluate(d, lib, tmp / f"{board}_r_{r}_{deg}")
                if st.built and st.errors and r not in [x[0] for x in rots]:
                    rots.append((r, deg))
                    emit(board, "rot", d, [f"layout.rotation.{r}={deg}"], "clean", st, lib)
        g0 = float(lay.get("gap_mm", 0.5))
        for g in (g0 * 6 + 1.5, 3.0):
            d = copy.deepcopy(desc0)
            d["layout"]["gap_mm"] = round(min(g, 3.0), 2)
            st = evaluate(d, lib, tmp / f"{board}_g")
            if not st.built:
                emit(board, "gap", d, [f"layout.gap_mm={d['layout']['gap_mm']} (was {g0})"], "clean", st, lib)
                break
        d = copy.deepcopy(desc0)
        d["layout"]["line"] = 1.0
        st = evaluate(d, lib, tmp / f"{board}_l")
        if not st.clean:
            emit(board, "line", d, [f"layout.line=1.0 (was {lay.get('line')})"], "clean", st, lib)
        d = copy.deepcopy(desc0)
        flip = "y" if lay.get("axis", "x") == "x" else "x"
        d["layout"]["axis"] = flip
        st = evaluate(d, lib, tmp / f"{board}_a")
        if not st.clean:
            emit(board, "axis", d, [f"layout.axis={flip}"], "clean", st, lib)
        if rots:
            d = copy.deepcopy(desc0)
            d["layout"]["rotation"] = {rots[0][0]: rots[0][1]}
            d["layout"]["gap_mm"] = round(min(g0 * 6 + 1.5, 3.0), 2)
            st = evaluate(d, lib, tmp / f"{board}_c")
            if not st.clean:
                emit(board, "combo", d, [f"layout.rotation.{rots[0][0]}={rots[0][1]}", f"layout.gap_mm={d['layout']['gap_mm']}"],
                     "clean", st, lib)
    (ROOT / "work/archive_tasks.json").write_text(json.dumps(made, indent=1))
    print(f"{len(made)} archive tasks")
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
