"""Mine a system's blind spots from its failed runs: group by family and failure, and show the evidence.

  python tools/blindspots.py --system lfm3 --track agent-eda [--results results/runs/agent-eda.jsonl ...]

For each failure it prints what the run left: the question it asked (ASK_PERSON.txt), its tool-call histogram, the
edits it tried, refusals, and its last words. Patterns to look for, each seen on 2026-11-22:
  escape hatch     asks a person about a value it should choose (LFM3 under pi)
  ignores a hint   moves away from the measured value (LFM3)
  dead-end loop    repeats a refused or worsening change (LFM3)
  over-exploring   reads source, emulates the tool, 100+ calls, times out (DeepSeek V4.1 Flash with raw tools)
  missing lever    never tries a key the fault needs, such as layout.axis (DeepSeek, LFM3)
  dropped params   leaves out an optional argument it was told to pass (DeepSeek with eda_change.key)
Write a patch for a pattern as a prompt overlay (edaagent/prompts/overlays/<model>.<surface>.md), then A/B it on
every task, not only the failures, and keep it only when it lifts the discriminating split without new failures.
"""
import argparse
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path.home() / "edaagent/eval"))
import pi_events  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--system", required=True)
    ap.add_argument("--track", required=True)
    ap.add_argument("--results", nargs="*", default=None)
    a = ap.parse_args()
    files = a.results or [str(p) for p in (ROOT / "results").rglob("*.jsonl")]
    latest = {}
    for f in files:
        for line in open(f):
            r = json.loads(line)
            if r.get("system") == a.system and r.get("track") == a.track and "task" in r:
                latest[r["task"]] = (r, f)
    fails = [(r, f) for r, f in latest.values() if not r["pass"]]
    print(f"{a.track} {a.system}: {len(fails)} failures of {len(latest)}")
    groups = collections.defaultdict(list)
    for r, f in fails:
        groups[(r["family"], r["why"].split(":")[0][:30], r["outcome"])].append(r)
    for (fam, why, outcome), rs in sorted(groups.items(), key=lambda x: -len(x[1])):
        print(f"\n## {fam}: {why} ({outcome}) x{len(rs)}")
        for r in rs[:3]:
            work = find_work(r)
            print(f"  {r['task']}")
            if not work:
                continue
            ask = work / "ASK_PERSON.txt"
            if ask.exists():
                print(f"    asked: {ask.read_text()[:200].strip()}")
            ev = work / "events.jsonl"
            if ev.exists() and a.track.startswith("agent"):
                s = pi_events.summarise(ev, show=False)
                hist = collections.Counter(c["tool"] for c in s["calls"])
                print(f"    calls: {dict(hist)}  turns {s['usage']['turns']}  tokens in {s['usage']['input']}")
                edits = [json.dumps(c["args"])[:110] for c in s["calls"] if c["tool"] in ("eda_change", "edit")][:5]
                for e in edits:
                    print(f"    edit: {e}")
                if s["says"]:
                    print(f"    last: {s['says'][-1][:200]}")
            elif ev.exists():
                for line in open(ev):
                    e = json.loads(line)
                    if e.get("ev") in ("candidate", "refused", "invalid"):
                        print(f"    {e['ev']}: {e.get('summary') or e.get('error', '')[:100]} -> "
                              f"{(e.get('build_error') or str([x['id'] for x in e.get('errors', [])]))[-90:]}")


def find_work(r):
    for base in [ROOT / "work" / r["track"] / r["system"].split("+")[0] / r["task"]]:
        if base.exists():
            return base
    arm = r.get("arm")
    if arm:
        d = Path.home() / "edaagent/runs" / r.get("tag", "") / arm.replace(":", "__").replace(",", "_").replace("=", "-").replace("+", "_") / r["task"]
        if d.exists():
            return d
    return None


if __name__ == "__main__":
    main()
