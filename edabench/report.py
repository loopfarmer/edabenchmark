"""Leaderboard: pass rate per (track, system) on each split, plus the decision track.

The latest row for each (track, system, task) wins, so a rerun replaces an older result.
"""
import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load():
    rows = []
    # Imported rows are the edaagent eval runs that seeded the splits, older than any benchmark run, so they load first
    # and a benchmark run of the same task replaces them.
    for p in sorted((ROOT / "results/imported").glob("*.jsonl")) + sorted((ROOT / "results/runs").glob("*.jsonl")):
        rows += [json.loads(l) for l in open(p)]
    return rows


def main(md: bool = False):
    man = {t["id"]: t for t in json.loads((ROOT / "tasks/manifest.json").read_text())["tasks"]}
    rows = load()
    latest = {}
    for r in rows:
        if "task" in r and r["task"] in man and not r.get("invalid"):
            latest[(r["track"], r["system"], r["task"])] = r
    splits = ["discriminating", "frontier", "smoke"]
    head = ["track", "system"] + splits + ["archive", "all", "med s", "$"]
    table = []
    for (track, system) in sorted({(k[0], k[1]) for k in latest}):
        rs = [r for k, r in latest.items() if k[0] == track and k[1] == system]
        cells = [track, system]
        for sp in splits:
            sub = [r for r in rs if man[r["task"]]["split"] == sp]
            total = sum(1 for t in man.values() if t["split"] == sp)
            cells.append(f"{sum(r['pass'] for r in sub)}/{len(sub)}" + ("" if len(sub) == total else f" of {total}"))
        arch = [r for r in rs if r["task"].startswith("archive-")]
        cells.append(f"{sum(r['pass'] for r in arch)}/{len(arch)}" if arch else "-")
        cells.append(f"{sum(r['pass'] for r in rs)}/{len(rs)}")
        secs = sorted(r.get("seconds", 0) for r in rs)
        cells.append(f"{secs[len(secs) // 2]:.0f}")
        cost = sum(u.get("cost_usd", 0.0) for r in rs for u in (r.get("usage") or {}).values() if isinstance(u, dict))
        cells.append(f"{cost:.4f}")
        table.append(cells)
    dec = collections.defaultdict(list)
    for r in rows:
        if r.get("track") == "decision":
            dec[r["system"]].append(r)
    if md:
        print("| " + " | ".join(head) + " |\n|" + "---|" * len(head))
        for c in table:
            print("| " + " | ".join(c) + " |")
    else:
        w = [max(len(str(x)) for x in col) for col in zip(head, *table)]
        for c in [head] + table:
            print("  ".join(str(x).ljust(k) for x, k in zip(c, w)))
    if dec:
        print("\ndecision track (latest run per system):")
        for s, rs in dec.items():
            tag = max(r["tag"] for r in rs)
            rs = [r for r in rs if r["tag"] == tag]
            print(f"  {s:16s} kind {sum(r['pass_kind'] for r in rs)}/{len(rs)}  person {sum(r['pass_person'] for r in rs)}/{len(rs)}"
                  f"  median {sorted(r['seconds'] for r in rs)[len(rs) // 2]}s  ${sum(r.get('cost_usd', 0) for r in rs):.5f}")
    return 0
