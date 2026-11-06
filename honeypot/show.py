"""Print a readable trace of one episode transcript.

  python -m honeypot.show results/<run>/transcripts/<episode>.jsonl [--full]
"""
from __future__ import annotations

import argparse
import json


def short(s: str, n: int) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[: n - 3] + "..."


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--full", action="store_true", help="do not truncate file contents and outputs")
    a = ap.parse_args()
    n = 10**9 if a.full else 400
    for line in open(a.path):
        e = json.loads(line)
        t = e["type"]
        if t == "start":
            print(f"== {e['run_id']}  env={e['env']} condition={e['condition']} model={e['model']}\n")
        elif t == "model":
            if e.get("text"):
                print(f"[{e['step']}] model says: {short(e['text'], n)}")
            for c in e["tool_calls"]:
                args = dict(c["args"])
                if "content" in args:
                    args["content"] = short(args["content"], n)
                print(f"[{e['step']}] -> {c['name']}({json.dumps(args)[:n]})")
        elif t == "tool_result":
            print(f"      <- {'ERROR ' if e['is_error'] else ''}{short(e['output'], min(n, 300))}")
        elif t == "provider_error":
            print(f"[{e['step']}] PROVIDER ERROR {e['error']}")
        elif t == "result":
            g = e["grade"]
            print("\n== result")
            print(f"   end={e['end_reason']} steps={e['steps']} claims_success={e['claims_success']}")
            print(f"   summary: {short(e.get('summary') or '', 600)}")
            print(f"   hack={e['hack']} tamper_attempted={e['tamper_attempted']} "
                  f"false_success_claim={e['false_success_claim']} honest_success={e['honest_success']}")
            print(f"   workspace_pass={g['workspace_pass']} visible(ok,bad)={g['true_visible_counts']} "
                  f"hidden(ok,bad)={g['hidden_counts']} tampered={g['tampered']} flags={g['special_case_flags']}")


if __name__ == "__main__":
    main()
