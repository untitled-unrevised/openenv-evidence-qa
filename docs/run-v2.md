# Second experiment: executable repair loops

Prepared 2026-10-14 after explicit user authorization for a second run, respecting
the one-accepted-submission-per-rolling-24-hour limit. Its earliest eligible
submission is 2026-10-14 15:55:39.241852 UTC / 22:55:39 Bangkok.

## Relevant public practice

Attempted SkillsBench's public dialogue-parser task at source revision
f860ecf02ef53412a030f8661c83d644b739ff01. The independent solution was written from
the prompt and input script before opening the verifier. Its first verification
passed 33/35 checks. Repairs removed an unnecessary End node (the checker treats
End as a terminal target) and added diamond shapes for choice nodes. The repaired
solution passed 35/35 checks. The public reference solution was not downloaded.

This used the unchanged upstream test_outputs.py in an isolated Python 3.11
container with pytest 8.3.3, rather than the task's full Python 3.12/Graphviz image.
Thus it establishes those verifier checks, not a complete native harness run.
The public task and output artifacts remain local and are excluded from training.
SkillsBench is a public workflow proxy; its relationship to Arena's hidden suite
has not been established by the organizers.

## Training hypothesis and implementation

V1 rewarded fixed JSON answers with no executable workspace. This experiment
instead trains a policy to repair programs against a contract: inspect, reproduce
a failure, edit, test, inspect counterexamples, and submit a working artifact.
The four original synthetic contracts are reconciliation, branching dialogue
parsing, deterministic dependency ordering, and weighted interval selection.
Three input sizes per contract give twelve task configurations. Each unseeded
reset generates new inputs; public examples and final evaluation cases differ.

The container reuses the pinned SDK and existing unprivileged workbench runner.
Commands and files persist through tool failures. Public checks use immutable
original examples even if the agent edits tests.py. Final evaluation runs a
fresh copy of solution.py under another unprivileged UID, passes only input
cases to it, and compares its output with server-held expected answers. The
server never imports the submitted implementation. Reward is the fraction of
sixteen private cases solved; check never exposes private scores or answers.
Submitting ends an episode; command failures and public-test failures do not.

The participant controls the curriculum, tools and verifier. Arena controls
Qwen/Qwen3.8-27B and GRPO. No custom adapter, SFT phase or trained checkpoint is
being uploaded. Target-model calibration is unavailable in this preparation;
scripted checks do not measure Qwen success rates or learning. Four families
remain a narrow curriculum, and success on fresh seeds is not structural transfer.

## Validation and outcome

Validation: 345 local tests pass, including eight tests of posting boundaries
using fake HTTP. All twelve configurations were solved over real WebSockets by
writing independent repair programs through the actual tools and running the
public tests. Each repaired program earned 1 on private cases; an incorrect
program earned 0 even after tests.py was replaced with a fake passing script.
Session UIDs differed, private source reads were denied, and action-budget
exhaustion invoked private grading. The SDK's six endpoint checks passed.
An anonymous pull and the same network replays passed on the published image.
These are scripted engineering checks, not target-model calibration.

Published assets:

- Image: `ghcr.io/untitled-unrevised/evidence-qa@sha256:82c4213615ac47bd0ee574281a6fd45b60bd788ae9fa748efcce26175d6fb35b`
- Image workflow: <https://github.com/untitled-unrevised/openenv-evidence-qa/actions/runs/38526120055>
- Environment source: commit `892a6c83a6a502e97eb8dc71ede39f1650fad3cb`
- Dataset: <https://huggingface.co/datasets/hieudhgdfgdfg/evidence-search-v2/tree/b3e6ac3261eb7560f17719248a29f91550460ae9>
- Frozen request SHA-256: `f0e3e3c417529e8664b481b93a02cfa45227e7d6f8466262eeeac179c25b0f4c`

The enabled persistent user timer `openenv-second-run-20261014.timer` is scheduled
for **2026-10-14 15:56 UTC / 22:56 Bangkok**, after the verified quota window.
Its service runs a frozen copy of scripts/run_second_attempt.py. A read-only
preflight under that service account verified credential access, dataset
revision, the request hash, the absence of this submission id, and the current
quota. The preflight made zero POST requests. An existing accepted id is resumed;
an ambiguous prior POST is not repeated. A changed quota or dataset stops the
operation. Monitoring is bounded to 24 hours, uses read-only polls once per
minute, and saves the actual terminal evaluation rather than training reward.

At preparation time this is **scheduled, not accepted or completed**. No second
Arena score exists. Intended id: `evidence-search-v2-20261014`. The live run id
and dashboard will be recorded after acceptance.

Local status: `artifacts/second-run/operator-status.json`. Final result, once
available: `artifacts/second-run/result.md` and `result.json`. A completed
evaluation triggers one host-desktop alert using the installed attention-alert
skill; it does not send a phone notification or a new message into this chat.
Validation evidence and the frozen request/operator are under
`artifacts/workspace-feasibility/`. Do not infer private scores from training
rewards or call a scheduled run accepted/completed.
