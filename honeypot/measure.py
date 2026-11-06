"""Run N episodes per (env, condition) and report rates with Wilson 95% CIs.

Examples:
  # offline, deterministic: checks the pipeline end to end
  python -m honeypot.measure --provider stub --policies honest,tamper,special_case,liar --n 2

  # real model (needs ANTHROPIC_API_KEY in the environment of THIS process)
  python -m honeypot.measure --provider anthropic --model claude-opus-5-5 --n 5 --workers 4

Writes results/<timestamp>_<provider>_<model>/{runs.jsonl,summary.md,transcripts/*.jsonl}.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .agent import run_episode
from .envs import CONDITIONS, ENV_NAMES, PROMPT_VARIANTS, make_env
from .providers import make_provider
from .stats import fmt_rate

MAX_REAL_RUNS = 40  # cost guard for real providers


def summarize(runs: list[dict], header: str) -> str:
    groups: dict[tuple, list[dict]] = {}
    for r in runs:
        groups.setdefault((r["env"], r["condition"], r.get("prompt_variant", "neutral"), r["model"]), []).append(r)
    lines = [header, "",
             "Rates are k/N (%) [Wilson 95% CI].", "",
             "| env | condition | prompt | model | N | hack | tamper attempted | false success claim | "
             "honest success | overfit | ended by | mean steps | tokens in/out |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for (env, cond, prompt, model), rs in sorted(groups.items()):
        n = len(rs)
        c = lambda key: sum(bool(r[key]) for r in rs)
        ends = {}
        for r in rs:
            ends[r["end_reason"]] = ends.get(r["end_reason"], 0) + 1
        tin = sum(r["usage"]["in"] for r in rs)
        tout = sum(r["usage"]["out"] for r in rs)
        lines.append(
            f"| {env} | {cond} | {prompt} | {model} | {n} | {fmt_rate(c('hack'), n)} | {fmt_rate(c('tamper_attempted'), n)} | "
            f"{fmt_rate(c('false_success_claim'), n)} | {fmt_rate(c('honest_success'), n)} | "
            f"{fmt_rate(c('overfit'), n)} | {', '.join(f'{k}:{v}' for k, v in sorted(ends.items()))} | "
            f"{sum(r['steps'] for r in rs) / n:.1f} | {tin:,}/{tout:,} |")
    lines += ["", "Per-run hack evidence:", ""]
    for r in runs:
        if r["hack"] or r["tamper_attempted"] or r["false_success_claim"]:
            g = r["grade"]
            ev = []
            if g["tampered"]:
                ev.append(f"tamper={ {k: v for k, v in g['tamper'].items() if v} }")
            if g["special_case_flags"]:
                ev.append(f"ast={g['special_case_flags'][:4]}")
            if r["tamper_attempted"]:
                ev.append(f"tamper_attempts={r['tamper_attempts']} refused={r['refused_writes']}")
            if r["false_success_claim"]:
                ev.append("claimed success; pristine grade visible="
                          f"{g['true_visible_counts']} hidden={g['hidden_counts']}")
            lines.append(f"- `{r['run_id']}` {r['env']}/{r['condition']}/{r['model']}: " + "; ".join(ev))
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", choices=["stub", "anthropic", "openai"], default="stub")
    ap.add_argument("--model", default=None)
    ap.add_argument("--effort", default="medium", help="Anthropic output_config.effort")
    ap.add_argument("--policies", default="honest", help="stub only: comma-separated policies")
    ap.add_argument("--envs", default=",".join(ENV_NAMES))
    ap.add_argument("--conditions", default=",".join(CONDITIONS))
    ap.add_argument("--prompt", choices=sorted(PROMPT_VARIANTS), default="neutral")
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--max-steps", type=int, default=20)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default="results")
    a = ap.parse_args(argv)

    envs = [e.strip() for e in a.envs.split(",") if e.strip()]
    conds = [c.strip() for c in a.conditions.split(",") if c.strip()]
    policies = [p.strip() for p in a.policies.split(",")] if a.provider == "stub" else [None]
    jobs = [(e, c, p, i) for e in envs for c in conds for p in policies for i in range(a.n)]

    if a.provider != "stub":
        key = "ANTHROPIC_API_KEY" if a.provider == "anthropic" else "OPENAI_API_KEY"
        if not os.environ.get(key):
            print(f"{key} is not set in this shell. Export it here first (it is never written to disk).",
                  file=sys.stderr)
            return 2
        if len(jobs) > MAX_REAL_RUNS:
            print(f"refusing {len(jobs)} real runs (cap {MAX_REAL_RUNS}); lower --n", file=sys.stderr)
            return 2

    model_tag = (a.model or ("claude-opus-5-5" if a.provider == "anthropic" else "stub")).replace("/", "_")
    out = Path(a.out) / f"{time.strftime('%Y%m%d-%H%M%S')}_{a.provider}_{model_tag}"
    (out / "transcripts").mkdir(parents=True, exist_ok=True)
    print(f"{len(jobs)} episodes -> {out}", flush=True)

    def one(job):
        e, c, p, i = job
        env = make_env(e)
        prov = make_provider(a.provider, a.model, env, policy=p, effort=a.effort)
        rid = f"{e}-{c}-{a.prompt}-{(p or model_tag)}-{i}"
        return run_episode(env, c, prov, max_steps=a.max_steps,
                           transcript_path=out / "transcripts" / f"{rid}.jsonl", run_id=rid,
                           prompt_variant=a.prompt)

    runs = []
    with ThreadPoolExecutor(max_workers=max(1, a.workers)) as ex, (out / "runs.jsonl").open("w") as f:
        futs = {ex.submit(one, j): j for j in jobs}
        for fut in as_completed(futs):
            try:
                r = fut.result()
            except Exception as exc:
                print(f"  episode {futs[fut]} crashed: {type(exc).__name__}: {exc}", flush=True)
                continue
            runs.append(r)
            f.write(json.dumps(r, default=str) + "\n")
            f.flush()
            print(f"  {r['run_id']}: end={r['end_reason']} steps={r['steps']} hack={r['hack']} "
                  f"claim={r['claims_success']} visible={r['grade']['true_visible_counts']} "
                  f"hidden={r['grade']['hidden_counts']}", flush=True)

    runs.sort(key=lambda r: r["run_id"])
    header = (f"## {a.provider} / {model_tag} / effort={a.effort if a.provider == 'anthropic' else '-'} / "
              f"prompt={a.prompt} / max_steps={a.max_steps} / {time.strftime('%Y-%m-%d %H:%M %Z')}")
    md = summarize(runs, header)
    (out / "summary.md").write_text(md + "\n")
    print("\n" + md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
