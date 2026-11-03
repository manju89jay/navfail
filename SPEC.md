# SPEC — navfail investigating agent (experiment build)

Classification: C/Build — one bounded new thing (log-reading agent + scoring harness) with one nameable interface, answering a fixed experiment question.

## Goal
Given one reproducible Nav2 failure folder, the agent proposes a configuration change from a fixed allowlist; scoring code proves or rejects it by repeated simulator runs, and a race compares the agent against random search.

## Non-goals
- Real robots; navigation beyond ROS 2 Jazzy / Nav2 1.3.13 / Gazebo.
- Explaining failures in prose beyond the candidate reason string.
- Touching frozen files: `reproduce/` (except adding an incident folder) and, after G1, the scoring files.
- Writing, editing or deleting run files under `incidents/*/runs/`.

## Decided & assumptions
- Decided: Agent model is Muse Wonder 1.0 (`muse-wonder-1.0`, Standard mode only) via Meta Model API at `https://api.meta.ai/v1`; OpenAI-compatible client; Structured Outputs (`response_format` json_schema) guarantee JSON-shaped candidates; reason string is data, not proof. Confirmed by the author on 28 Oct 2026. EXPERIMENT.md section 6 says "Muse Spark" — update that page to record the Wonder change, or the race will contradict the spec.
- Pricing (Meta docs, verified 28 Oct 2026): Wonder Standard $4 / 1M input, $0.20 / 1M cached input, $20 / 1M output; Spark Standard $1.25/$4.25 for reference; 1,048,576-token context window; rate limit 3,000 RPM / 4M TPM per team.
- Decided: API key works. The author set `MODEL_API_KEY` in their own terminal; a key check run there on 28 Oct 2026 returned model `muse-wonder-1.0`, 28 input + 16 output tokens. The key is never visible to Muse's sandbox shell (separate Windows user) and must stay out of code, logs and commits.
- OPEN-3: Failure F — S1 still open. 0.50 m doorway resists all fixes; 0.60 m passes. No F, no race.
- OPEN-4: Cache prefix — prompt starts with a stable prefix (system rules + allowlist + deployed config) to hit cached-input rate and cut latency; must be identical across candidates in a search. Confirm byte-stability of that prefix in the implementation.

## Interface
`investigate(incident_dir, config, allowlist) -> {"changes": {setting: value}, "reason": "..."}` as strict JSON; scoring `verify.py` recomputes every reported number from run files only.

## Checks
1. Agent returns schema-valid JSON for a canned incident folder without any simulator run; invalid output triggers exactly one retry, then the proposal counts as used.
2. `verify.py` recomputes a known-good candidate verdict from existing run files and matches the recorded `result.json` (reached goal, no stall >= 15 s, collision check vs `groundtruth.csv` + walls).
3. Proof rule boundary: stall of exactly 15.0 s counts as failure; 14.9 s does not (same convention both sides).
4. Runner refuses a second concurrent simulator with exit 2; started runs are never killed by another runner.
5. Race accounting: every simulator run (screening included) increments the 40-run budget; search stops at first proven fix or budget end.
6. No number appears in the final report that `verify.py` cannot reproduce from run files.

## Edge cases
- Nav2 never ready (`NOT_READY`) or no goal reply (`NO_GOAL_REPLY`): run counts toward budget, recorded, never retried for a better result.
- Crashed simulator run: rerun, crash recorded; never silently dropped.
- Candidate outside allowlist or range: rejected before any run; counts as used.
- Two configurations compared: same config against itself is the control; verdict is descriptive only (5 searches per arm).

## Success number
Race completes with verdict "fewer" / "not fewer" / "inconclusive" per EXPERIMENT.md section 7, every number recomputed by `verify.py`; worst case 400 sim runs (7–10 h), expected stop earlier on first proven fix.

## After launch
Overnight run monitored via run files only; spend stop at $90 (EXPERIMENT.md rule 7); demo video recorded after S6 report is approved by the author.

---
### Recommended workflow with Muse models (groundwork finding)
1. Separate thinking from simulation. The model never touches the simulator; it only sees curated text: operator note, filtered `nav2.log` (error/warning lines + timeline window), `groundtruth`-derived timeline numbers, deployed `nav2_params.yaml`, allowlist. Keep each prompt at ~20–50k tokens despite the 1M context window — cost and latency stay trivial and the signal stays clean.
2. Put the stable prefix first (system rules + allowlist + config) and cache it; candidates then differ only in the short suffix (run results so far). This is where prompt caching pays.
3. Constrain decoding with Structured Outputs (`response_format` json_schema), not prompt-and-parse. No regex scraping; invalid JSON is impossible by construction, so the one-retry rule is only for out-of-range values.
4. Reasoning effort: `max` (author set the maximum on 3 Nov 2026; a live probe confirmed this key accepts `max` for `muse-wonder-1.0`). Candidates are proposals inside a tiny allowlist; changing the effort does not affect the proof rule. Simulator runs remain the real bottleneck (1–1.5 min each, one at a time).
5. Verdict before narrative: `verify.py` recomputes scores from run files; prose is written last from verified numbers only.

### Budget for this build (one full experiment)
- API dollars: expected well under $35 total on Wonder Standard (worst case ~200 calls x ~35k input + ~1k output ≈ 7M input + 0.2M output ≈ $32; with caching, less). Your check call above (44 tokens) cost about $0.0004.
- Time: build S2–S4 is days, not hours; race is 7–10 h overnight worst case. Simulation, not tokens, is the scarce resource.
- Guardrails: $100 Billing-page cap set at G0; hard stop at $90; one simulator at a time (exit 2 = wait, never kill).

## Plan

S2 only (S3/S4 build on these contracts unchanged). Pure core, files at the edge: geometry, stall and verdict logic are pure functions over parsed values; only `verify.py` and the run-file loader touch disk. Conventions already in the repo are followed, not re-invented: stall and goal logic mirror `reproduce/observe.py` (`STILL_RADIUS_M = 0.10`, `GOAL_TOLERANCE_M = 0.25`, integer `t_ms`), wall geometry mirrors `reproduce/sim_assets.py` (axis-aligned boxes `{cx, cy, sx, sy}`), tests are plain pytest functions like `reproduce/test_observe.py`. Failure F is `incidents/C-corridor`, synthetic in every label.

Components (contract first):

1. **Allowlist** — data + validation. In: a candidate `{"changes": {setting: value}}`. Out: the same dict, or `ValueError` naming the offending setting. Holds the six settings of EXPERIMENT.md section 4 with stock values, allowed ranges (inclusive both ends) and the `nav2_params.yaml` paths they write to (inflation settings write both costmaps together). Errors: unknown setting, non-numeric value, value outside range, 0 or more than 3 changes.
2. **Run scoring (pure)** — In: `(nav2_result, trace[(t_ms, x, y)], goal, walls)`. Out: `{reached_goal, longest_still_ms, min_wall_clearance_m, collided, passed}`. `reached_goal` iff `nav2_result == "SUCCEEDED"` and final distance to goal <= 0.25 m. Stall failure iff `longest_still_ms >= 15000` (15.0 s inclusive, SPEC check 3). `collided` iff the robot centre comes within the robot radius 0.22 m of any wall rectangle (clearance < 0.22 m; no walls means never collided). A run `passed` iff reached, no stall failure and not collided.
3. **Run-file loader** — In: incident dir + run dir. Out: the pure inputs above plus a `kind`: `valid`, `not_ready` (`NOT_READY`), `no_goal_reply` (`NO_GOAL_REPLY`), `runner_error`, or `incomplete` (no `result.json`: not a run, ignored). Reads only `result.json`, `groundtruth.csv` and `incident.json`; never writes under `incidents/*/runs/`.
4. **Candidate verdict + run counting** — In: scored site runs + scored empty-site runs. Out: `{proven, site_passed, site_valid, collisions, empty_passed, runs_counted}`. Proven iff at least 4 of the first 5 valid site runs passed, no valid site run collided, and 3 of 3 valid empty-site runs reached the goal (EXPERIMENT.md section 5). `runs_counted` counts every run folder holding a `result.json` (screening, `not_ready` and `no_goal_reply` included) against the 40-run budget; `incomplete` folders count 0.
5. **`experiment/verify.py` (CLI boundary)** — In: an incident dir (and optionally explicit run dirs). Out: JSON on stdout recomputing every run's `reached_goal`/`longest_still_ms` from `groundtruth.csv` alone, compared against the recorded `result.json`; exit 0 when every recomputed value matches, 1 on any mismatch, 2 on usage error. No number exists in any later report that this tool did not recompute (SPEC check 6).

File map (every file S2 creates or modifies; anything else touched is an unordered change):

- `experiment/__init__.py` — package marker so arms and tests import one place.
- `experiment/allowlist.py` — component 1 (settings, ranges, YAML paths, validation).
- `experiment/scoring.py` — components 2–4 (pure scoring, loader, verdict, counting).
- `experiment/verify.py` — component 5 (CLI; the only S2 file that writes to stdout as a program).
- `experiment/tests/test_scoring.py` — tests for components 1–4, including integration tests over the recorded runs in `incidents/A-doorway` and `incidents/B-drop-off` (read-only).
- `experiment/tests/test_verify.py` — tests for component 5 over copies in `tmp_path` (never over the real run folders).
- `SPEC.md` — this Plan/Tasks section only.
- `docs/EXPERIMENT.md` — S2 freeze only: SHA-256 of the scoring files written into section 8/S2 when T6 lands.

Remaining design question (answerable, A or B): does a collision in a 5th site run that otherwise passes 4 of 5 void the proof? Chosen reading: yes — section 5 rule 2 says "No run collides", unqualified, so any collision among valid site runs voids `proven` even when rule 1 is met. Revisited only if G2 dry-run evidence shows this reading contradicting the lab's recorded fixes.

Plan: 5 components, 8 files mapped. Next: /tasks.

## Tasks

Dependency-ordered; one task = one commit leaving the repo green; tests first (red, then green) in every task.

### T1 — Proof-rule core (pure stall / goal / pass logic)
- **Does:** Adds `experiment/scoring.py` with the pure run-scoring function (component 2, trace part) and the exact 15.0 s boundary.
- **Files:** `experiment/__init__.py`, `experiment/scoring.py`, `experiment/tests/test_scoring.py`
- **Tests first:** `test_stall_of_exactly_15_0s_is_a_failure`, `test_stall_of_14_9s_is_not_a_failure`, `test_reached_requires_succeeded_and_within_goal_tolerance`, `test_pass_requires_reached_no_stall_no_collision` — all written and seen failing before the code.
- **Hands off:** `reproduce/`, all of `incidents/`, collision geometry (T2), disk access of any kind.
- **Proves:** SPEC check 3 (both boundary sides, same convention); edge case "same config against itself" is untouched here.

### T2 — Collision check against ground truth and walls
- **Does:** Extends `scoring.py` with wall-clearance geometry (component 2, wall part): distance from each trace point to each wall rectangle, minimum clearance, `collided` below the 0.22 m robot radius.
- **Files:** `experiment/scoring.py`, `experiment/tests/test_scoring.py`
- **Tests first:** `test_collision_when_clearance_below_robot_radius`, `test_no_collision_at_exactly_robot_radius`, `test_trace_inside_wall_collides`, `test_no_walls_never_collides`, `test_clearance_uses_nearest_wall`.
- **Hands off:** `reproduce/`, `incidents/`, the T1 stall/goal logic, `experiment/verify.py` (does not exist yet).
- **Proves:** SPEC check 2's collision half; EXPERIMENT.md section 5 rule 2 as scored from `groundtruth.csv` + `incident.json` walls.

### T3 — Run-file loader against the recorded A/B runs
- **Does:** Adds the loader (component 3) to `scoring.py`: reads `result.json` + `groundtruth.csv` + `incident.json`, classifies `valid` / `not_ready` / `no_goal_reply` / `runner_error` / `incomplete`, and scores valid runs through T1+T2.
- **Files:** `experiment/scoring.py`, `experiment/tests/test_scoring.py`
- **Tests first:** `test_recorded_A_runs_recompute_to_recorded_result_json` (all 3 A runs: recomputed `reached_goal` and `longest_still_ms` equal the recorded values), `test_recorded_B_runs_all_fail_the_proof_scoring` (3 of 3 not reached), `test_not_ready_run_is_classified_and_not_scored`, `test_folder_without_result_json_is_incomplete`.
- **Hands off:** writing anything under `incidents/*/runs/` (loader is read-only; tests only read), `reproduce/`, verdict/counting (T4).
- **Proves:** SPEC check 2 (recompute matches recorded `result.json` on known runs); edge cases `NOT_READY` / `NO_GOAL_REPLY` classification (recorded, never scored as passes).

### T4 — Candidate verdict and run counting
- **Does:** Adds component 4 to `scoring.py`: proof-rule verdict over scored runs (4 of 5 site, any-collision voids, 3 of 3 empty) and budget counting where every `result.json` folder counts, screening included.
- **Files:** `experiment/scoring.py`, `experiment/tests/test_scoring.py`
- **Tests first:** `test_proven_needs_four_of_five_site_passes`, `test_three_of_five_is_not_proven`, `test_any_collision_voids_proof`, `test_proven_needs_three_of_three_empty_site`, `test_every_result_json_counts_toward_budget_including_screening_and_not_ready`, `test_incomplete_folder_counts_zero`.
- **Hands off:** `experiment/verify.py`, both arms, the simulator (no runs are started in S2).
- **Proves:** SPEC check 5's counting half (every run increments the budget) and check 2's verdict half; EXPERIMENT.md section 5 evaluation order is represented as data (screening runs are simply the first counted runs).

### T5 — `verify.py` recomputes every number from run files only
- **Does:** Adds `experiment/verify.py` (component 5): walks an incident's run folders, recomputes `reached_goal` / `longest_still_ms` / clearance per run from `groundtruth.csv`, compares with recorded `result.json`, prints the recomputation as JSON, exits 0/1/2 as contracted.
- **Files:** `experiment/verify.py`, `experiment/tests/test_verify.py`
- **Tests first:** `test_verify_matches_recorded_A_incident`, `test_verify_reports_mismatch_and_exits_1` (on a `tmp_path` copy with one doctored value), `test_verify_ignores_folder_without_result_json`, `test_verify_usage_error_exits_2`.
- **Hands off:** the real run folders (tests copy files to `tmp_path`; the CLI itself only reads), `scoring.py` logic (verify calls it, never duplicates it).
- **Proves:** SPEC checks 2 and 6 (any report number is reproducible by this tool from run files alone).

### T6 — Freeze the scoring files
- **Does:** Runs the full S2 suite in WSL, computes SHA-256 of `experiment/allowlist.py`, `experiment/scoring.py`, `experiment/verify.py` and the two test files, and writes those hashes into `docs/EXPERIMENT.md` step S2; after this commit those files are frozen (EXPERIMENT.md section 9 rule 3).
- **Files:** `docs/EXPERIMENT.md`, `experiment/allowlist.py` (created here if T1–T5 did not need it — it is created in T1's commit if validation tests land there; this task only hashes what exists and must not edit the hashed files)
- **Tests first:** none new — the gate is the whole suite green in WSL (`python3 -m pytest experiment/ -q`) plus `verify.py` exit 0 over both `incidents/A-doorway` and `incidents/B-drop-off`.
- **Hands off:** the scoring files themselves (a hash written for a file edited in the same commit is no freeze), `reproduce/`, `incidents/*/runs/`.
- **Proves:** EXPERIMENT.md S2 "Done when" (tests pass; SHA-256 of the scoring files in the page); SPEC check 6's freeze precondition.

Allowlist validation (component 1) lands inside whichever of T1/T4 first needs it — planned for T4, where "candidate outside allowlist or range: rejected before any run; counts as used" becomes testable as `test_candidate_outside_allowlist_rejected_before_any_run` against `experiment/allowlist.py`; if it lands earlier it moves with its tests, and T6 hashes it either way.

Tasks: 6 tasks, checks covered 4 of 6 (checks 1 and 4 belong to S4 and the frozen runner respectively; check 5's search-stop half belongs to S3/S4). Next: /audit.
