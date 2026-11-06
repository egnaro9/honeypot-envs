"""Re-score saved episodes with the current labels. No API calls.

    python -m honeypot.rescore            # every results/*_anthropic_*/runs.jsonl

Recomputes the honesty labels from each episode's saved grade, tamper log and
submission. The grade itself is not recomputed: solutions are not re-run here.
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

from .labels import honesty_labels


def load(pattern: str = "results/*_anthropic_*/runs.jsonl") -> list[dict]:
    runs = []
    for path in sorted(glob.glob(pattern)):
        for line in open(path):
            r = json.loads(line)
            r.update(honesty_labels(r["claims_success"], r["summary"], r["grade"]["tamper"], r["honest_success"]))
            runs.append(r)
    return runs


def table(runs: list[dict]) -> str:
    groups: dict[tuple, list[dict]] = {}
    for r in runs:
        groups.setdefault((r["model"], r["env"], r["condition"], r.get("prompt_variant", "neutral")), []).append(r)
    out = ["| model | env | condition | prompt | N | hack | false success claim (v1) | "
           "misleading success claim (v2) | disclosed edit | covert edit |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for (model, env, cond, prompt), rs in sorted(groups.items()):
        n = len(rs)
        c = lambda k: sum(bool(r[k]) for r in rs)
        out.append(f"| {model} | {env} | {cond} | {prompt} | {n} | {c('hack')}/{n} | {c('false_success_claim')}/{n} | "
                   f"{c('misleading_success_claim')}/{n} | {c('disclosed_edit')}/{n} | {c('covert_edit')}/{n} |")
    tot = lambda k: sum(bool(r[k]) for r in runs)
    out.append(f"| **all** | | | | {len(runs)} | {tot('hack')} | {tot('false_success_claim')} | "
               f"{tot('misleading_success_claim')} | {tot('disclosed_edit')} | {tot('covert_edit')} |")
    return "\n".join(out)


if __name__ == "__main__":
    runs = load(sys.argv[1] if len(sys.argv) > 1 else "results/*_anthropic_*/runs.jsonl")
    print(table(runs))
