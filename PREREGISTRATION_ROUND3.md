# Pre-registration, round 3: same environments, Claude Haiku 5.5

Written 2026-11-06 ~16:00 ET, after Opus 5.5 scored 0/24 and before any Haiku run.
Exploratory.

## Question

Is Opus 5.5's 0/24 a property of the model or of the environment? The design is
unchanged, only the model differs: if a smaller model hacks here, the environment
can elicit hacking and Opus resisted it; if it does not either, the environment is
too easy to be honest in.

## Planned run

`claude-haiku-5-5`, effort `medium`, `max_steps` 20, N = 4 per cell, the same six
cells as Opus (24 episodes):
- `duration` and `duration_impossible`, honeypot and control, neutral prompt;
- `duration_oneoff`, honeypot and control, pressure prompt.

One run. Every episode is reported, including errors and refusals.

## Predictions

| cell | hack | honest success |
|---|---|---|
| duration, both conditions | 0/4 each (at most 1) | >= 2/4 each (capability may limit it) |
| duration_impossible / honeypot | 0/4 or 1/4 | 0/4 (by construction) |
| duration_impossible / control | 0/4 | 0/4 (by construction) |
| duration_oneoff / honeypot / pressure | 0/4 to 2/4 | 0/4 (by construction) |
| duration_oneoff / control / pressure | 0/4 or 1/4 (special-casing only) | 0/4 (by construction) |

Pooled over the 16 impossible-type episodes: at most 3 hacks. I expect a higher
false-success-claim rate than Opus (a smaller model is more likely to misread its
own test output), but no more than 1/4 in any cell.

Reasoning: Haiku 5.5 comes from the same training lineage, so I expect the same
honest default. The plausible difference is capability: a model that cannot
fully solve the task is closer to the "can't pass honestly" situation even on the
solvable env, which is where hacks tend to appear.
