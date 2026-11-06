# The honeypot's own checks, run through Erik's eval tools (2026-11-06)

The tools ran from local copies of `~/evalmut`, `~/gradecore`, `~/deadgate` and
`~/deadcheck`, installed into an isolated venv; their source trees were not modified.
Every finding was re-run in a separate pass and labelled before acting on it.

## evalmut: the pristine grader

The target is the harness-side code that turns the sandbox driver's stdout into a
verdict: `parse_driver_stdout` + `score_outputs`. Suite: `evals/evalmut_suite.py`,
8 cases (6 numeric answers, 2 expected `ValueError`).

| pass | applied | caught | blind spots | brittle | n/a |
|---|---|---|---|---|---|
| 1 | 40 | 32 | 0 | 8 | 136 |
| 2 (suite declaration corrected) | 24 | 24 | 0 | 0 | 152 |

- **Blind spots: 0 in both passes.** No injected wrong output was graded as a pass.
- **The 8 brittle flags in pass 1: ARTIFACT.** All 8 came from `identical_to_reference`,
  which replaced the driver's line with the bare answer (`5400`). Re-run directly:
  `parse_driver_stdout("5400", 1)` returns `None`, so the score is (0 ok, 1 bad),
  while the wire format `HP_RESULT [{"v": 5400}]` scores (1, 0). The grader rejects
  anything not in the driver's structured format on purpose: accepting free text
  from stdout would reopen the fake-output hole the hack zoo found. The suite had
  declared `expected` as the bare answer. Pass 2 declares it in the wire format,
  and the flags disappear.
- Caveat: the corrected declaration applies fewer operators (24 vs 40), so pass 2
  is a narrower test, not a strictly stronger one.

## deadgate: does not apply

`deadgate ~/honeypot-envs` reports "no workflow files under .github/workflows" (exit 0).
The repo has no CI, so there is no CI check that could be unable to fail.

## deadcheck: not run

deadcheck scores a rubric against a pack of labelled specimens. The closest thing
here is the hack zoo (`honeypot/zoo.py`): 12 planted hacks and 4 honest cases,
hand-written by the same author as the detectors. Porting the zoo to a deadcheck
pack, and adding specimens written by someone else, is the next step. It is
also the fix for the zoo's main weakness: an author grading their own detectors.
