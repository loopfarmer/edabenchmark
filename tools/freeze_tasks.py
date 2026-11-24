"""Freeze the task set and assign splits from recorded results.

  python tools/freeze_tasks.py [--results results/runs/*.jsonl ...]

Copies edaagent's generated tasks (eval/tasks) in beside the archive tasks already here, hashes every description and
footprint library, and writes tasks/manifest.json. A task's split comes from every recorded result for it:

  discriminating  at least one system passed it and at least one failed: it separates systems (the default split)
  smoke           every system passed: a check that the harness works, not a measure
  frontier        no system has passed it yet (or it was built to be unsolved): kept to catch a stronger system
  unscored        no results yet
  pending         the task needs edaloop changes the pin doesn't have yet: its task.json `requires` names them, and it
                  counts once pins.json lists each under edaloop.includes. Runs skip it, even with --split all.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EDAAGENT_TASKS = Path.home() / "edaagent/eval/tasks"


def digest(d: Path) -> str:
    h = hashlib.sha256()
    for f in sorted(p for p in d.rglob("*") if p.is_file() and p.name != "task.json"):
        h.update(f.relative_to(d).as_posix().encode())
        h.update(f.read_bytes())
    return h.hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", nargs="*", default=None)
    a = ap.parse_args()
    out = ROOT / "tasks"
    out.mkdir(exist_ok=True)
    for d in sorted(EDAAGENT_TASKS.iterdir()):
        if d.is_dir() and (d / "task.json").exists():
            shutil.rmtree(out / d.name, ignore_errors=True)
            shutil.copytree(d, out / d.name)
    files = a.results if a.results is not None else [str(p) for p in (ROOT / "results/runs").glob("*.jsonl")]
    files += [str(p) for p in (ROOT / "results/imported").glob("*.jsonl")]
    outcomes: dict[str, dict[str, bool]] = defaultdict(dict)
    for f in files:
        for line in open(f):
            r = json.loads(line)
            if "task" not in r:
                continue
            system = r.get("system") or r.get("arm")
            outcomes[r["task"]][f"{r.get('track', 'harness')}|{system}"] = bool(r["pass"])
    pins = json.loads((ROOT / "pins.json").read_text())
    have = set(pins.get("edaloop", {}).get("includes", []))
    tasks = []
    for d in sorted(out.iterdir()):
        if not (d / "task.json").exists():
            continue
        t = json.loads((d / "task.json").read_text())
        res = outcomes.get(t["id"], {})
        if not res:
            split = "frontier" if t["family"] == "frontier" else "unscored"
        elif all(res.values()):
            split = "smoke"
        elif not any(res.values()):
            split = "frontier"
        else:
            split = "discriminating"
        missing = [x for x in t.get("requires", {}).get("edaloop", []) if x not in have]
        if missing:
            split = "pending"
        tasks.append({"id": t["id"], "board": t["board"], "family": t["family"], "expect": t["expect"],
                      "faults": t["faults"], "parts": t.get("parts"), "split": split, "sha": digest(d),
                      "systems_passed": sum(res.values()), "systems_run": len(res),
                      **({"requires": t["requires"]} if t.get("requires") else {})})
    (out / "manifest.json").write_text(json.dumps({"pins": pins, "tasks": tasks}, indent=1))
    counts = defaultdict(int)
    for t in tasks:
        counts[t["split"]] += 1
    print(f"{len(tasks)} tasks: {dict(counts)}")


if __name__ == "__main__":
    main()
