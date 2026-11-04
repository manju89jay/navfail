# SPEC — warehouse sandbox test on an internet-sourced failure

Classification: C/Explore — one bounded experiment reusing the frozen scoring, search loop and simulator bridge on a new site; the deliverable is an answer, not new product code.

## Goal
Build a warehouse-style site in the sandbox, take one navigation failure from a public internet report (not planted by us, not the corridor), reproduce its symptom there, and test whether the log-reading agent finds a proven fix in fewer simulator runs than random search.

## Non-goals
- No edit to the frozen scoring files, `reproduce/` (except adding an incident folder, which the frozen rule allows), or any existing incident's run files.
- No change to the six-setting allowlist, the proof rule, or the 40-run budget.
- No claim that the sandbox rebuild is the reporter's exact setup; it is a symptom rebuild, labelled with its source.
- One failure, one search per arm. No five-search race for this test.

## Decided & assumptions
- Decided (author, 3 Nov 2026): map is a warehouse built in the existing harness — shelf rows as wall boxes in the TB3 sandbox with a warehouse-style map — because the stock TB4 warehouse world needs a different robot and edits to the frozen harness.
- Decided (author): the failure is a seeded random pick from a shortlist of public Nav2 failure reports whose symptom can plausibly be rebuilt and retried in simulation. The pick and seed are recorded before any run.
- Decided (author): scope is one 40-run search per arm (agent vs random), every number recomputed by `experiment/verify.py`, and the comparison draft stops for author review.
- Decided: deployed configuration for the warehouse incident follows the picked report's mechanism as closely as the frozen allowlist/harness allows; any planted element is labelled, with the source URL recorded in the incident folder.
- Decided: if the picked symptom cannot be reproduced after a bounded site-tuning attempt (aisle width steps), the test ends as "does not reproduce" and the next shortlist entry is NOT silently substituted — that is reported to the author.

## Checks
1. Recorded pick: the seeded selection from the shortlist, with source URL, is written into the warehouse work folder before the first run folder exists.
2. Reproduction gate: 5 baseline runs of the warehouse incident's deployed config on a copy produce at least 4 failures under the frozen scoring. Below 4, no search starts and the test ends as "does not reproduce".
3. Frozen judge: SHA-256 of the five frozen files still matches `docs/EXPERIMENT.md` section 8 before the first search runs.
4. Both arms finish: each search ends proven at a stated run count ≤ 40, or with 40 runs used and no proven fix. Every `result.json` run is counted; none deleted or rerun for a better result.
5. Verified numbers: `experiment/verify.py` exits 0 on every candidate folder of both searches, and each search's folder run count equals its `search.json` `runs_used`.

## Edge cases
- Baseline run not ready or no goal reply: recorded, rerun for the same slot, never counted as a failure or a pass.
- No allowlisted fix exists: both arms use their budget and report "none" — a valid negative answer.
- Network loss during an agent search: attempt folders preserved and excluded, search restarted.
- A collision in any valid site run voids that candidate's proof, even at 4 of 5 passes.

## Success number
One warehouse incident sourced from a public report, reproduction gate passed (≥4 of 5 baseline failures), both arms completed within budget, 100% of reported runs recomputed by `verify.py` with zero mismatches, and a stated comparison: agent runs to proven fix vs random runs to proven fix, or "none" per arm.

## After launch
Result confirmed only from run files in the warehouse work folder; the comparison is drafted from `verify.py` output and stops for author review before anything is published.

## What shipped
- Checks satisfied: 2 of 5 (40%) — recorded seeded pick (#4938, seed 20261104, before any run) and verified-numbers machinery throughout; the reproduction gate was run three times and honestly failed each time.
- Outcome: **does not reproduce.** Aisle widths 1.1 m, 0.8 m and 0.7 m each passed 5 of 5 baseline runs with stock configuration; no arm search was started, per check 2.
- Divergences: first site placement was invalid (stock sandbox obstacles crossed the aisle; planner could not plan) — preserved as `baseline-attempt1-blocked-site` and excluded, then the aisle was moved to the proven clear band and narrowed in steps.
- Not implemented, and why: the agent-vs-random comparison on this failure — the gate it depends on never passed, and substituting another failure silently was explicitly excluded by this spec.
- Follow-ups discovered: the picked report's mechanism is DWB-specific; a future pick should require the reporter's controller to match the sandbox stack (MPPI), or the incident must carry the reporter's controller configuration.
