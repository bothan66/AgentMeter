# Reproduction scope

Current example release: 16 description pairs are public; the complete
64-description archive is not included. Local tests and eight mock pipeline
attempts passed after this change. A live Docker/API run is still unverified:
this execution session receives permission denied on the Docker socket and
cannot request elevated access. This does not establish that Docker is
unavailable to the user outside this session.

| Goal | Included | Remaining requirement |
|:--|:--|:--|
| Inspect the method | Optimizer, metrics, adapters, examples | None |
| Recompute released descriptive tables | Self aggregate and 192 Cross task records; `scripts/reproduce_artifact_table.py` | No API |
| Replay selected Original/Self/Cross examples | 16 task bundles and 16 optimized descriptions | Docker, patched Harbor, provider access; full description grid not released |
| Regenerate a candidate | Optimizer and safety gate | Original trajectory, reflection API |
| Run Core30 / Full80 | Exact task ID lists and suite launcher | Matching external task checkout |
| Recompute every paper number | Partial result artifacts | Core/Full run-level records, exact historical scoring/pricing settings, Self task-level records |

Run `python scripts/reproduce_artifact_table.py` to print the released
descriptive tables. Archived monetary values are CNY. They must not be compared
directly to USD values in the manuscript. The archived
`self_summary.csv:AgentMeterScore` field has not been reconciled with the
manuscript AMS table; the table script deliberately does not present it as
paper AMS. `scripts/compute_scores.py` produces basic pass/token summaries,
not a complete paper AMS reproduction.

Candidate-only optimization generates an instruction without target evaluation.
To measure quality or efficiency, replay that instruction through the task
verifier. A lexical safety gate is not proof of semantic equivalence; expanded
artifact-derived descriptions require task-level review.

A previous local Docker oracle check reached the verifier for
`lru-cache-with-ttl` and passed 14 of 15 checks (reward 0). The failing check
was `test_evict_all_expired_picks_oldest`. The original task is preserved;
this is a known reference-solution issue, not a successful full-pass smoke.
A clean external-machine API rerun has not been verified for this release.

Development validation is `python -m pip install -e '.[dev]'` followed by
`pytest -q` and `python scripts/public_release_check.py`. These checks
validate code and artifact consistency; they do not establish live API success.

Release check on 2026-09-14: 16 tests passed, including selection cardinality,
the then-complete 64 description pairs, the unique 192-condition Cross grid, retained task
snapshots, and duplicate-output protection. The Harbor patch passed
`git apply --check` against the four files at the documented base revision.
The descriptive-table command and publication scan also passed.
