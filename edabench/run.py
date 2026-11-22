"""edabenchmark runner.

  edabench run --track harness   --model lfm3            [--split discriminating|smoke|all] [--workers 4] [--tag T]
  edabench run --track agent-eda --model ds41-1017       (pi + the edaagent tools)
  edabench run --track agent-raw --model inkling-loom    (pi + bash/read/edit/write + edaloop's SKILL.md)
  edabench run --track decision  --model d1-ultra
  edabench run --track harness   --model lfm3 --escalate inkling-loom --decider d1-ultra   (a system, not a model)
  edabench report [--md]

Models are named in models.json; add one there (any OpenAI-compatible endpoint, or a System One decision endpoint).
Every run appends one row per task to results/runs/<track>.jsonl with the pins it ran under.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MODELS = json.loads((ROOT / "models.json").read_text())
PINS = json.loads((ROOT / "pins.json").read_text())

from edaagent import config as ea_config, description as dsc, state as stt, tiers  # noqa: E402
from edaagent.driver import fix  # noqa: E402

EDAAGENT = Path(ea_config.ROOT)
PI_RAW_PROMPT = """Fix the placement of the circuit board described in description.yaml in this folder.

- Build it with `edaloop build description.yaml -o board` (add `--footprints lib` when a lib folder is here) and check it
  with `edaloop -C board --json critic`.
- Edit only description.yaml. Rebuild after every change (the build replaces the board folder).
- You are done when the build succeeds and the critic reports no errors: then write a one-line summary to DONE.txt.
- If a value or decision belongs to a person, write the exact question to ASK_PERSON.txt and stop. Never invent a value.
The edaloop skill describes the tools."""
REFINE_HINT = """
- If the critic still reports errors that no description change clears (a part in the way of an RF line), you may run
  `edaroute refine board/<name>.kicad_pcb board/chains_<name>.yaml refined/<name>.kicad_pcb --budget 120` with
  PYTHONPATH set to edaloop's src. Put the whole board folder, with the refined board in it, in ./refined."""


def manifest() -> list[dict]:
    return json.loads((ROOT / "tasks/manifest.json").read_text())["tasks"]


def select(split: str, only: str = "") -> list[dict]:
    ts = manifest()
    ts = ts if split == "all" else [t for t in ts if t["split"] == split]
    if only:
        keys = set(only.split(","))
        ts = [t for t in ts if t["id"] in keys or t["family"] in keys or t["board"] in keys
              or any(t["id"].startswith(k) for k in keys)]
    return ts


def register_tier(name: str) -> None:
    m = MODELS["chat"][name]
    tiers.TIERS[name] = {"base_url": m["base_url"], "model": m["model"], "reasoning": m.get("reasoning"),
                         "max_tokens": m.get("max_tokens", 1000), "extra": m.get("extra"),
                         "api_key_env": m.get("api_key_env"), "remote": "openrouter" in m["base_url"],
                         "schema": m.get("schema", True)}


def score(task: dict, work: Path) -> dict:
    orig = dsc.load(ROOT / "tasks" / task["id"] / "description.yaml")
    try:
        final = dsc.load(work / "description.yaml")
    except Exception as e:
        return {"pass": False, "why": f"description unreadable: {e}"}
    prot = dsc.protected_diff(orig, final)
    asked = (work / "ASK_PERSON.txt").exists()
    if task["expect"] == "ask":
        ok = asked and not prot
        return {"pass": ok, "why": "asked, nothing invented" if ok else ("changed " + ",".join(prot) if prot else "did not ask")}
    st = stt.evaluate(work / "description.yaml", work / ".score-build")
    refined = None
    if not st.clean and st.built and not prot and not asked and (work / "refined").is_dir():
        from edaagent import refine as rf
        refined = rf.verify(work, Path(st.board))
    ok = (st.clean or bool(refined and refined["ok"])) and not prot and not asked
    why = (("clean" if st.clean else refined["why"]) if ok else (refined["why"] if refined else "")) or ("clean" if ok else "asked instead" if asked else "changed " + ",".join(prot) if prot
           else "build failed" if not st.built else f"{len(st.errors)} critic errors")
    return {"pass": ok, "why": why}


def run_harness(work: Path, model: str, escalate: str | None, decider: str | None, overlay: bool = False,
                refine: bool = False) -> dict:
    if model == "none":           # no model: build, then edaroute refine alone
        rec = fix(work / "description.yaml", work / ".fix", max_steps=0, log_path=work / "events.jsonl", refine=True)
        return {"outcome": rec["outcome"], "steps": 0, "usage": {}, "refine": rec.get("refined")}
    register_tier(model)
    if escalate:
        register_tier(escalate)
        mode = "d1+signals" if decider else "signals"
        pol = tiers.Policy(mode=mode, ladder=(model, escalate), decider=decider or "d1-local")
    else:
        pol = tiers.Policy(mode=f"always:{model}")
    rec = fix(work / "description.yaml", work / ".fix", policy=pol, log_path=work / "events.jsonl", overlay=overlay,
              refine=refine)
    if rec["outcome"] == "ask_person":
        (work / "ASK_PERSON.txt").write_text(str(rec["question"]) + "\n")
    usage = dict(rec["usage"])
    if pol.decider_usage:
        usage["decider"] = pol.decider_usage
    return {"outcome": rec["outcome"], "steps": rec["steps"], "usage": usage,
            "escalations": sum(1 for p in pol.log if "escalate_to" in p), "refine": rec.get("refined")}


def pi_agent_dir(model: str) -> Path:
    m = MODELS["chat"][model]
    d = ROOT / "work/.pi-agent" / model
    d.mkdir(parents=True, exist_ok=True)
    prov = {"baseUrl": m["base_url"], "api": "openai-completions",
            "apiKey": f"${m['api_key_env']}" if m.get("api_key_env") else "local",
            "models": [{"id": m["model"], "contextWindow": 65536, "maxTokens": 8192, "reasoning": True,
                        "input": ["text"], "thinkingLevelMap": {"off": "none", "low": "low"},
                        "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
                        **({"compat": m["pi_compat"]} if m.get("pi_compat") else {})}]}
    (d / "models.json").write_text(json.dumps({"providers": {"bench": prov}}, indent=1))
    (d / "settings.json").write_text(json.dumps({"quietStartup": True, "packages": [], "extensions":
                                                 ["-builtin:mcp", "-builtin:llama.cpp", "-builtin:codemode", "-builtin:tool-search"]}))
    return d


def overlay_file(model: str, surface: str) -> Path | None:
    stem = {"ds41-1017": "ds41", "inkling-loom": "inkling", "inkling-or": "inkling", "lfm3-or": "lfm3"}.get(model, model)
    f = EDAAGENT / "prompts/overlays" / f"{stem}.{surface}.md"
    return f if f.exists() else None


def run_pi(work: Path, model: str, raw: bool, timeout: float, overlay: bool = False, refine: bool = False) -> dict:
    sys.path.insert(0, str(EDAAGENT / "eval"))
    import pi_events
    env = dict(os.environ, PI_CODING_AGENT_DIR=str(pi_agent_dir(model)), EDAAGENT_MAX_TURNS="16",
               PATH=f"{ea_config.EDALOOP.parent}:{os.environ['PATH']}")
    cmd = ["pi", "--mode", "json", "--no-session", "-nc", "-ns", "-na", "--provider", "bench",
           "--model", MODELS["chat"][model]["model"], "--thinking", "off"]
    if raw:
        cmd += ["--skill", str(ea_config.EDALOOP_REPO / "src/edaloop/agent"), "--tools", "read,bash,edit,write"]
        prompt = PI_RAW_PROMPT + (REFINE_HINT if refine else "")
    else:
        tools = "eda_status,eda_change,eda_revert,eda_ask_person,eda_finish" + (",eda_refine" if refine else "")
        cmd += ["-e", str(EDAAGENT / "pi/edaagent")] + (["-e", str(EDAAGENT / "pi/edaagent-refine")] if refine else [])
        cmd += ["--tools", tools, "--system-prompt", str(EDAAGENT / "prompts/pi_system.md")]
        prompt = "Fix this board's placement." + (" If critic errors remain that no layout change clears, try eda_refine." if refine else "")
    ov = overlay_file(model, "pi") if overlay else None
    if ov:
        cmd += ["--append-system-prompt", str(ov)]
    cmd.append(prompt)
    with open(work / "events.jsonl", "w") as out, open(work / "pi.err", "w") as err:
        try:
            rc = subprocess.run(cmd, cwd=work, env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            rc = 124
    s = pi_events.summarise(work / "events.jsonl", show=False)
    outcome = ("ask_person" if (work / "ASK_PERSON.txt").exists() else "done" if (work / "DONE.txt").exists()
               else "max_turns" if (work / "MAX_TURNS.txt").exists() else "timeout" if rc == 124 else f"exit {rc}")
    return {"outcome": outcome, "steps": len(s["calls"]), "usage": {"pi": s["usage"]}}


def one(track: str, model: str, task: dict, args) -> dict:
    tag = args.tag or time.strftime("%Y%m%d")
    work = ROOT / "work" / track / (model + ("+overlay" if args.overlay else "") + ("+refine" if args.refine else "")) / task["id"]
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    shutil.copy(ROOT / "tasks" / task["id"] / "description.yaml", work / "description.yaml")
    if (ROOT / "tasks" / task["id"] / "lib").is_dir():
        shutil.copytree(ROOT / "tasks" / task["id"] / "lib", work / "lib")
    t0 = time.time()
    try:
        if track == "harness":
            r = run_harness(work, model, args.escalate, args.decider, args.overlay, args.refine)
        else:
            r = run_pi(work, model, raw=track == "agent-raw", timeout=args.timeout, overlay=args.overlay, refine=args.refine)
    except Exception as e:
        r = {"outcome": f"crash: {type(e).__name__}: {e}"[:300]}
    r["seconds"] = round(time.time() - t0, 1)
    r.update(score(task, work))
    system = (model + (f"+esc:{args.escalate}" if args.escalate else "") + (f"+{args.decider}" if args.decider else "")
              + ("+overlay" if args.overlay else "") + ("+refine" if args.refine and model != "none" else ""))
    if model == "none":
        system = "refine-only"
    if isinstance(r.get("refine"), dict) and r["refine"].get("board"):
        r["refine"]["board"] = str(Path(r["refine"]["board"]).relative_to(ROOT)) if str(r["refine"]["board"]).startswith(str(ROOT)) else "refined"
    r.update({"track": track, "system": system, "task": task["id"], "family": task["family"], "split": task["split"],
              "tag": tag, "pins": {"edaloop": PINS["edaloop"]["commit"][:9]}})
    return r


def run_decision(model: str, args) -> list[dict]:
    cases = json.loads((ROOT / "decisions/cases.json").read_text())
    spec = MODELS["decision"][model]
    tiers.DECIDERS[model] = {"url": spec["url"], "model": spec["model"], "api_key_env": spec["api_key_env"]}
    qs = cases["questions"]
    rows = []
    for c in cases["cases"]:
        usage: dict = {}
        t0 = time.time()
        ans = tiers.d1_decide(c["state"], qs, decider=model, usage=usage, timeout=60)
        dt = round(time.time() - t0, 2)
        if not ans:
            rows.append({"case": c["id"], "pass_kind": False, "pass_person": False, "answered": False, "seconds": dt})
            continue
        kind = ans["kind"].get("choice")
        person = float(ans["person"].get("noul", 0)) >= 0.5
        rows.append({"case": c["id"], "kind": kind, "want_kind": c["kind"], "pass_kind": kind == c["kind"],
                     "p_person": round(float(ans["person"].get("noul", 0)), 3), "want_person": c["person"],
                     "pass_person": person == c["person"], "answered": True, "seconds": dt,
                     "cost_usd": usage.get("cost_usd", 0.0)})
    tag = args.tag or time.strftime("%Y%m%d")
    for r in rows:
        r.update({"track": "decision", "system": model, "tag": tag})
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(prog="edabench")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--track", required=True, choices=["harness", "agent-eda", "agent-raw", "decision"])
    r.add_argument("--model", required=True)
    r.add_argument("--escalate", default=None, help="harness track: a stronger chat model to escalate to")
    r.add_argument("--decider", default=None, help="harness track with --escalate: a decision model gating escalation")
    r.add_argument("--split", default="discriminating", choices=["discriminating", "smoke", "all"])
    r.add_argument("--workers", type=int, default=4)
    r.add_argument("--timeout", type=float, default=600)
    r.add_argument("--tag", default=None)
    r.add_argument("--refine", action="store_true", help="edaroute refine after the description loop (harness), or the eda_refine tool (agent tracks); --model none runs refine alone")
    r.add_argument("--overlay", action="store_true", help="append the model's prompt overlay (edaagent/prompts/overlays)")
    r.add_argument("--only", default="", help="comma list of task ids, families, boards or id prefixes")
    rep = sub.add_parser("report")
    rep.add_argument("--md", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "report":
        from .report import main as rmain
        return rmain(a.md)
    out = ROOT / "results/runs" / f"{a.track}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    if a.track == "decision":
        rows = run_decision(a.model, a)
        with open(out, "a") as f:
            for row in rows:
                f.write(json.dumps(row) + "\n")
        print(f"{a.model}: kind {sum(r['pass_kind'] for r in rows)}/{len(rows)}, person {sum(r['pass_person'] for r in rows)}/{len(rows)}")
        return 0
    tasks = select(a.split, a.only)
    print(f"{a.track} {a.model}: {len(tasks)} tasks ({a.split})", flush=True)
    with cf.ThreadPoolExecutor(a.workers) as ex, open(out, "a") as f:
        for fut in cf.as_completed([ex.submit(one, a.track, a.model, t, a) for t in tasks]):
            row = fut.result()
            f.write(json.dumps(row) + "\n")
            f.flush()
            print(f"{'PASS' if row['pass'] else 'fail'} {row['task']:36s} {row['outcome']:12s} {row['why'][:40]} {row['seconds']}s",
                  flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
