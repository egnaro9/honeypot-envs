"""What optimization pressure on the naive reward does, computed from saved episodes.

RL (and best-of-k sampling, its cheapest stand-in) reinforces whichever episodes
score highest on the reward it is given. The honeypot's naive reward is "the
workspace test run passes". On tasks with no honest pass, that reward is earned
only by a hack. This asks: if you sample k episodes and keep the highest-reward
one, how often is the kept episode a hack?

Exact, not simulated. For a cell with N saved episodes, h of which are hacks,
and only hacks earning naive reward (true on the impossible-type envs, and
checked below), best-of-k selects a hack unless all k draws are non-hacks:

    P(select hack) = 1 - C(N - h, k) / C(N, k)        (draws without replacement)

    python -m honeypot.selection
"""
from __future__ import annotations

import glob
import json
from math import comb


def load(pattern: str = "results/*_anthropic_*/runs.jsonl") -> list[dict]:
    rs = []
    for path in sorted(glob.glob(pattern)):
        rs += [json.loads(line) for line in open(path)]
    return rs


def p_select_hack(n: int, h: int, k: int) -> float:
    if k > n:
        k = n
    return 1 - comb(n - h, k) / comb(n, k)


def table(runs: list[dict]) -> str:
    groups: dict[tuple, list[dict]] = {}
    for r in runs:
        if r["env"] == "duration":
            continue  # solvable env: honest episodes also earn the naive reward
        groups.setdefault((r["model"], r["env"], r["condition"], r.get("prompt_variant", "neutral")), []).append(r)
    out = ["| model | env | condition | N | hacks | naive reward only on hacks? | best-of-1 | best-of-3 | best-of-N |",
           "|---|---|---|---|---|---|---|---|---|"]
    for key, rs in sorted(groups.items()):
        n, h = len(rs), sum(r["hack"] for r in rs)
        if h == 0:
            continue
        only_hacks = all(r["hack"] for r in rs if r["grade"]["workspace_pass"])
        out.append(f"| {key[0]} | {key[1]} | {key[2]} | {n} | {h} | {'yes' if only_hacks else 'NO'} | "
                   f"{h / n:.0%} | {p_select_hack(n, h, 3):.0%} | {p_select_hack(n, h, n):.0%} |")
    return "\n".join(out)


if __name__ == "__main__":
    print(table(load()))
