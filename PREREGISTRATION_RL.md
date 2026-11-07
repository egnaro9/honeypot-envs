# Pre-registration: strategy-level RL against the honeypot

Written 2026-11-06 ~22:05 ET, before the first run of `honeypot/rl_strategy.py`.

## What it is, and what it is not

REINFORCE over a softmax policy that picks one of four scripted strategies per task:
honest, tamper (rewrite the test), special_case (look up visible answers), or
precompute_table (round 5's import-time table). There is one policy per task family:
impossible speed, impossible duration, feasible speed.

Every reward comes from a real rollout: real sandbox, real tests, real out-of-process
grader. Rollouts are cached per (task, strategy). This is **not** RL on a language
model. It tests the claim the README makes about training: the naive reward teaches
hacking and the true reward does not.

Settings: 9 tasks (3 per family), 600 iterations, learning rate 0.5, RNG seed 0,
trained once with each reward.

## Predictions

- **Naive reward, impossible families:** the policy concentrates on whichever arms
  pass the workspace tests. Expected hack rate at the end: at least 0.9 on both
  impossible families.
- **True reward, impossible families:** no arm ever earns true reward there, so the
  gradient is zero and the policy stays near uniform. The hack rate stays at
  roughly the share of arms that hack (about 0.5-0.75). **The true reward stops
  paying for hacks, but on tasks with no honest success it does not teach the policy
  to avoid them.** Avoiding them needs either feasible tasks to learn from or an
  explicit penalty.
- **Feasible family:** under the naive reward there is little pressure between
  honest, tamper and precompute_table, since all pass the workspace, so the hack
  rate stays mixed (0.2-0.5). Under the true reward, tamper earns 0 while honest and
  the cold-start-legal table earn 1, so the hack rate falls below 0.1.
