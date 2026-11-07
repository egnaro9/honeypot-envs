"""Policy-gradient learning over strategies, against the real honeypot.

This is the smallest honest RL experiment this laptop can run. It is NOT RL on a
language model: the policy picks one of a few scripted strategies per task, and
learns which to pick from reward. Every reward comes from a real rollout: real
sandbox, real tests, real out-of-process grader.

  arms:    honest | tamper (rewrite the test) | special_case (lookup of visible
           answers) | precompute_table (import-time table, round 5's trick)
  tasks:   procgen.generate(seed): impossible speed, impossible duration, feasible speed
  policy:  softmax over arms per task family (a contextual bandit), trained with
           REINFORCE and a per-family running-mean baseline
  rewards: naive (the workspace tests pass) vs true (pristine pass, no hack flagged)

Rollouts are cached per (task, strategy): the scripted strategies are deterministic,
so a cached reward equals a fresh one up to timing noise.

    python -m honeypot.rl_strategy --iters 600
"""
from __future__ import annotations

import argparse
import json
import math
import random
import time
from pathlib import Path

from . import procgen
from .gym_env import HoneypotGymEnv, scripted_policy

ARMS = ("honest", "tamper", "special_case", "precompute_table")


def family(env_name: str) -> str:
    return env_name.rsplit("_", 1)[0]


def rollout(seed: int, arm: str) -> dict:
    env_spec = procgen.generate(seed)
    g = HoneypotGymEnv(task_fn=procgen.generate, reward_mode="naive")
    g.reset(seed=seed)
    info, last_pass = {}, False
    try:
        for act in scripted_policy(arm, env_spec):
            if act["args"] is None:
                act = {"name": "submit", "args": {"success": last_pass, "summary": "Reported test status."}}
            obs, _r, term, trunc, info = g.step(act)
            if act["name"] == "run_tests":
                last_pass = obs.startswith("PASSED")
            if term or trunc:
                break
    finally:
        g.close()
    return {"seed": seed, "family": family(env_spec.name), "arm": arm,
            "naive": info.get("reward_naive", 0.0), "true": info.get("reward_true", 0.0), "hack": bool(info.get("hack"))}


def build_table(seeds: list[int]) -> list[dict]:
    return [rollout(s, a) for s in seeds for a in ARMS]


def softmax(xs):
    m = max(xs)
    e = [math.exp(x - m) for x in xs]
    z = sum(e)
    return [v / z for v in e]


def train(table: list[dict], reward: str, iters: int, lr: float, seed: int) -> dict:
    rng = random.Random(seed)
    by_task = {}
    for row in table:
        by_task.setdefault(row["seed"], {})[row["arm"]] = row
    seeds = sorted(by_task)
    fams = sorted({row["family"] for row in table})
    theta = {f: [0.0] * len(ARMS) for f in fams}
    baseline = {f: 0.0 for f in fams}
    curve = []
    for t in range(iters):
        s = rng.choice(seeds)
        fam = by_task[s][ARMS[0]]["family"]
        p = softmax(theta[fam])
        a = rng.choices(range(len(ARMS)), weights=p)[0]
        r = by_task[s][ARMS[a]][reward]
        adv = r - baseline[fam]
        baseline[fam] += 0.05 * (r - baseline[fam])
        for k in range(len(ARMS)):  # REINFORCE for a softmax policy: grad log p(a) = 1[k=a] - p_k
            theta[fam][k] += lr * adv * ((1.0 if k == a else 0.0) - p[k])
        if t % 25 == 0 or t == iters - 1:
            curve.append({"iter": t, **{f: expected(theta[f], by_task, f) for f in fams}})
    return {"theta": theta, "policy": {f: dict(zip(ARMS, softmax(theta[f]))) for f in fams},
            "final": {f: expected(theta[f], by_task, f) for f in fams}, "curve": curve}


def expected(theta_f, by_task, fam) -> dict:
    """Expected hack rate, naive reward and true reward of the current policy on a family."""
    p = softmax(theta_f)
    rows = [arms for arms in by_task.values() if arms[ARMS[0]]["family"] == fam]
    n = len(rows)
    out = {}
    for key in ("hack", "naive", "true"):
        out[key] = round(sum(p[i] * float(arms[ARMS[i]][key]) for arms in rows for i in range(len(ARMS))) / n, 3)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=9, help="task pool size (cycles the 3 families)")
    ap.add_argument("--iters", type=int, default=600)
    ap.add_argument("--lr", type=float, default=0.5)
    ap.add_argument("--rng", type=int, default=0)
    ap.add_argument("--out", default="results")
    a = ap.parse_args()
    t0 = time.time()
    table = build_table(list(range(a.seeds)))
    runs = {mode: train(table, mode, a.iters, a.lr, a.rng) for mode in ("naive", "true")}
    out = Path(a.out) / f"rl_strategy_{time.strftime('%Y%m%d-%H%M%S')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"args": vars(a), "arms": ARMS, "table": table, "runs": runs,
                               "seconds": round(time.time() - t0, 1)}, indent=1))
    print("reward table (real rollouts):")
    print("| seed | family | " + " | ".join(f"{arm} naive/true/hack" for arm in ARMS) + " |")
    by_seed = {}
    for row in table:
        by_seed.setdefault((row["seed"], row["family"]), {})[row["arm"]] = row
    for (s, f), arms in sorted(by_seed.items()):
        cells = [f"{arms[x]['naive']:.0f}/{arms[x]['true']:.0f}/{'H' if arms[x]['hack'] else '-'}" for x in ARMS]
        print(f"| {s} | {f} | " + " | ".join(cells) + " |")
    print("\nafter training, per family: P(arm), then the policy's expected hack rate, naive and true reward")
    for mode, r in runs.items():
        print(f"\n[{mode} reward]")
        for f, pol in r["policy"].items():
            fin = r["final"][f]
            print(f"  {f:16s} " + "  ".join(f"{k}={v:.2f}" for k, v in pol.items())
                  + f"  | hack={fin['hack']:.2f} naive={fin['naive']:.2f} true={fin['true']:.2f}")
    print(f"\nwrote {out} ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
