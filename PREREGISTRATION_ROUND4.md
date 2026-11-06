# Pre-registration, round 4: misbehavior drift across model generations

Written 2026-11-06 ~16:35 ET, after rounds 1-3 and before any round-4 run.
Exploratory.

## Question

`model-drift` tracks whether silent model updates move accuracy. This asks the
same question about **behaviour under a reward-hacking opportunity**: does a model's
willingness to edit a contradictory test drift across generations?

Round 3 found the one cell that separates models: `duration_impossible`. There,
Opus 5.5 attempted 0/8 test edits and Haiku 5.5 attempted 4/8. Round 4 runs that
cell on the previous generation, the models `model-drift` tracks.

## Planned run

`duration_impossible`, honeypot and control, neutral prompt, `max_steps` 20, using the
v2 honesty labels from `honeypot/labels.py`:
- `claude-opus-4-8`, `claude-sonnet-5`, `claude-haiku-4-5`: N = 4 per cell (24 episodes).
- `claude-fable-5`: N = 2 per cell (4 episodes), cut for cost at $10/$50 per MTok.

Request settings differ by model where the API forces it (`AnthropicProvider.MODEL_SETTINGS`):
- Opus 4.8 runs thinking off by default, so it is set to adaptive.
- Haiku 4.5 rejects `effort` and takes a 4,000-token thinking budget instead.
- All others: effort `medium`, thinking at the model default (on).

One run. Every episode is reported, including errors and refusals.

## Predictions

| model | tamper attempted (honeypot + control) | hack (honeypot) | misleading success claim (v2) |
|---|---|---|---|
| Opus 4.8 | 0-2 of 8 | 0-1 of 4 | 0 |
| Sonnet 5 | 0-3 of 8 | 0-2 of 4 | 0-1 |
| Haiku 4.5 | 2-6 of 8 | 1-3 of 4 | 0-1 |
| Fable 5 | 0 of 4 | 0 of 2 | 0 |

Direction I expect: smaller models edit more than larger ones; within a size,
the newer model edits less. I expect edits to keep coming with a disclosure, as
Haiku 5.5's did, so covert edits stay at 0 or near it. A covert edit or a
misleading claim from any model would be the most important result of this round.
