# V2 draft: persistent tool work

This branch keeps v1's twelve tasks and verifier while changing how the policy
can work. It is an environment experiment, not an evaluated improvement. No v2
image, dataset, or Arena submission has been published.

## Existing options inspected

The installed OpenEnv SDK and its pinned upstream PythonCodeAct executor were
inspected. The latter uses a restricted local Python interpreter and does not
provide the shell and file workflow wanted here. Public pinned source from
rca-umb/five-desks-code and akseljoonas/mimo-openenv-software was also inspected:
both use container commands under an unprivileged UID and private graders.
The skills catalog surfaced no installed runner that adds this task contract.

Choice: reuse the pinned SDK and existing task/verifier code, with a small
independently written container adapter following that established separation.
No new skill, plugin, agent framework or evaluation framework is installed.

## Agent capabilities

`list`, `read`, `write`, `shell`, `check`, `submit`, `finish`.

- Shell commands can invoke Python, Git and installed Unix tools. Python's
  standard library includes SQLite, decimal arithmetic, JSON, CSV and unittest.
- Files and scripts persist across calls within an episode.
- Each session gets a separate workspace and UID. A reset removes its files.
- A command error or timeout returns feedback without ending the episode.
- `check` validates report.json without terminating. An incorrect `submit`
  also leaves the episode open. Correct submission ends with reward 1.
- `finish` and the 64-action limit grade the current artifact.
- A command has a 10-second timeout, resource limits, a sanitized environment,
  bounded retained output and a short observation.

Commands run only in the dedicated root-run Docker container. Local host calls
are refused. The grader package is root-only, and report reads reject symlinks,
hard links, nonregular files and oversized files. The workspace's parent stays
server-owned to prevent a rename-and-symlink replacement. These controls rely
on the outer container for host isolation; they are not a claim of complete
containment of arbitrary hostile code. Outbound network is not blocked here.

## Run and verify

```sh
docker build -f Dockerfile.workbench -t openenv-evidence-workbench:v2-local .
docker run --rm -p 127.0.0.1:8929:8000 openenv-evidence-workbench:v2-local
.venv/bin/python scripts/workbench_check.py
.venv/bin/openenv validate --url http://127.0.0.1:8929
.venv/bin/python -m pytest tests -q
```

Verified locally: 298 tests, including 39 workbench tests; all twelve tasks were
solved over real WebSockets by writing and executing reference scripts through
the actual agent tools. Those episodes first attempted bad JSON submission and
a failing command, then recovered and produced the correct report. Additional
container checks covered independent session UIDs, denied grader access, denied
workspace-root rename, and recovery after a real 10-second command timeout.
The pinned SDK runtime validator passed all six endpoint checks.

These are scripted tool/reward checks, not model calibration or proof of transfer.

## Next experiment

Prepare a v2 request with 64 actions and a larger but measured token budget, then
calibrate against the target model's exact action parser and thinking settings.
Use separate unseen workflows to assess transfer. Keep this task set for an
initial controlled tool-access comparison; structural diversity is a subsequent
change. Investigate the clipping metric before treating larger budgets as a fix.

The score target is nine credited domain solves (22.5%), because forty equally
weighted private tasks yield 2.5-point increments. The leaderboard stores best
domain results across runs. That aggregate is distinct from a single model's
score, and selected noisy domain bests do not establish a training gain.
