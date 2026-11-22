"""Import edaagent eval results (~/edaagent/results/*.jsonl) as benchmark rows in results/imported/.

Arm names map to (track, system):
  driver:mode=never,ladder=M            -> harness, M
  driver:mode=always:T                  -> harness, T
  driver:mode=signals,ladder=M+E        -> harness, M+esc:E
  driver:mode=d1+signals,decider=D,...  -> harness, M+esc:E+D
  driver:...,person=0                   -> harness, ...+noperson (the model, not a rule, decides to ask)
  pi-eda:model=M / pi-raw:model=M       -> agent-eda / agent-raw, M
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = {"lfm3": "lfm3", "inkling": "inkling-loom", "ds41": "ds41-1017", "ds41-1017": "ds41-1017"}


def system_of(arm: str) -> tuple[str, str]:
    kind, _, rest = arm.partition(":")
    o = dict(kv.split("=", 1) for kv in rest.split(",") if "=" in kv)
    if kind in ("pi-eda", "pi-raw"):
        return ("agent-eda" if kind == "pi-eda" else "agent-raw"), NAMES.get(o.get("model", "lfm3"), o.get("model"))
    mode = o.get("mode", "never")
    ladder = [NAMES.get(x, x) for x in o.get("ladder", "lfm3").split("+")]
    if mode.startswith("always:"):
        s = NAMES.get(mode.split(":", 1)[1], mode.split(":", 1)[1])
    elif mode == "never":
        s = ladder[0]
    else:
        s = f"{ladder[0]}+esc:{ladder[-1]}" + (f"+{o.get('decider', 'd1-local')}" if mode.startswith("d1") else "")
    if o.get("person") == "0":
        s += "+noperson"
    return "harness", s


def main(paths):
    out = ROOT / "results/imported"
    out.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(out / "edaagent.jsonl", "w") as f:
        for p in paths:
            for line in open(p):
                r = json.loads(line)
                if "arm" not in r:
                    continue
                track, system = system_of(r["arm"])
                r.update({"track": track, "system": system, "tag": Path(p).stem, "source": "edaagent eval"})
                f.write(json.dumps(r) + "\n")
                n += 1
    print(f"imported {n} rows")


if __name__ == "__main__":
    main(sys.argv[1:] or sorted(str(p) for p in (Path.home() / "edaagent/results").glob("r*.jsonl")))
