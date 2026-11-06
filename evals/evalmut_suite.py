"""evalmut suite for the honeypot's pristine grader (harness side).

The grader under test is the code that turns the sandbox driver's stdout into a
pass/fail verdict: `parse_driver_stdout` + `score_outputs`. Each case is a
driver stdout the grader passes today; evalmut injects known-wrong (and
known-still-correct) mutations and reports what the grader lets through.

    evalmut run evals/evalmut_suite.py -v
"""
from __future__ import annotations

import json

from gradecore import GradeInput, Verdict

from evalmut import EvalCase
from honeypot.detectors import score_outputs
from honeypot.sandbox import parse_driver_stdout


def _grader_for(text_input: str, expected):
    def grade(inp: GradeInput) -> Verdict:
        outs = parse_driver_stdout(inp.text or "", 1)
        ok, bad = score_outputs([(text_input, expected)], [], outs)
        passed = bad == 0
        return Verdict(passed=passed, score=1.0 if passed else 0.0,
                       severity="none" if passed else "high", detail="",
                       grader_id="honeypot_pristine_grader")
    return grade


def _stdout(value) -> str:
    rec = {"e": "ValueError"} if value == "ValueError" else {"v": value}
    return "HP_RESULT " + json.dumps([rec])


CASES = [("PT1H30M", 5400), ("45:00", 2700), ("1w2d", 777600), ("90s", 90), ("300", 300),
         ("1d 2h 3m 4s", 93784), ("-5m", "ValueError"), ("5x", "ValueError")]

suite = [
    EvalCase(
        f"driver-{text}",
        _grader_for(text, expected),
        # `expected` is declared in the driver's wire format, the only format this grader
        # accepts (first pass declared the bare answer; see evals/EVAL_REPORT.md).
        GradeInput(text=_stdout(expected), expected=_stdout(expected)),
        content_required=True,
        grader_family="exact",
        tolerates=("whitespace", "reserialize"),
    )
    for text, expected in CASES
]
