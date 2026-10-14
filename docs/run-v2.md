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

Also attempted the public exam-block-sequencing task from that revision. A
65-second vectorized simulated-annealing search produced a feasible 24-block
schedule that passed the public reference-quality threshold. Its first report
misinterpreted the overlap objective and failed the metrics-consistency check
(reported 3019 versus verifier-recomputed 4034). After consulting the public
verifier to clarify the objective, a second 65-second search optimized the full
formula and produced objective 3971. The unchanged verifier then passed all
three checks: reported objective, feasibility, and reference-quality threshold.
No optimality proof is claimed. The reference solution was not read. Verification
again used an isolated Python 3.11/pytest container with the actual task data and
unchanged verifier, not the full native task harness. Files and traces remain
local under artifacts/workspace-feasibility/. This public task is not in training.

## Published target-model diagnostic evidence

Inspected the peer-published calibration at
<https://huggingface.co/datasets/rca-umb/five-desks-code/tree/e042d726112949e78c10efdb53d0a7c012809eab/calibration>.
Its r2 files report Qwen/Qwen3.8-27B:deepinfra solving 38/72 episodes, with a
lenient parser and rescued replies. Reported endings include 17 schema-invalid,
6 no-JSON, 3 truncated, and 7 out-of-steps episodes. One schema failure emitted
`{"tool":"exec","cmd":"ls src/isodate"}` instead of the required nested
arguments; one no-JSON failure emitted prose proposing an experiment instead
of an executable action. These are concrete examples of action-interface and
budget failures alongside genuine successful code repair. They do not establish
the cause of Arena's low score. This is third-party evidence, not independently
reproduced inference or calibration of our new curriculum, and its lenient parser
is not the Arena contract. These traces are not incorporated into training.

## Training hypothesis and implementation

V1 rewarded fixed JSON answers with no executable workspace. This experiment
instead trains a policy to repair programs against a contract: inspect, reproduce
a failure, edit, test, inspect counterexamples, and submit a working artifact.
The four original synthetic contracts are reconciliation, branching dialogue
parsing, deterministic dependency ordering, and weighted interval selection.
Three size levels per contract give twelve task configurations. The pre-run audit
added eight structural scenario patterns per family; see [pre-run audit](pre-run-audit.md). Each unseeded
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

Validation after the pre-run audit: 352 local tests pass, including eight tests of posting boundaries
using fake HTTP. All twelve configurations were solved over real WebSockets by
writing independent repair programs through the actual tools and running the
public tests. Each repaired program earned 1 on private cases; an incorrect
program earned 0 even after tests.py was replaced with a fake passing script.
Session UIDs differed, private source reads were denied, and action-budget
exhaustion invoked private grading. The SDK's six endpoint checks passed.
An anonymous pull and the same network replays passed on the published image.
The revised source also passed a second-seed replay and the published image
passed a third-seed replay. CI now checks the actual repair loop before publishing.
These are scripted engineering checks, not target-model calibration.

Published assets:

- Image: `ghcr.io/untitled-unrevised/evidence-qa@sha256:2fe294a5c86b89a5be2480171c2131d17c5a4ecb9348b7b1ff4606d4de086f50`
- Image workflow: <https://github.com/untitled-unrevised/openenv-evidence-qa/actions/runs/38534465998>
- Environment source: commit `7587f9b516915e3c588ace6473b20038bf2aa45a`
- Dataset: <https://huggingface.co/datasets/hieudhgdfgdfg/evidence-search-v2/tree/ea2a38abf4b7be0226e3d70f8349a94afda94593>
- Frozen request SHA-256: `b6bb409b4d93642877003a4df042679db383fc0e43b91ca6b576fd05056b6093`

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

The pre-run audit found four contract-violating shortcuts with full reward on
480/480 original cases each. Revised generators reject each shortcut, and visible
tests now match final numeric typing and save concise counterexample artifacts.
The active pins above supersede the original prepared pins, preserved in Git
history and artifacts/pre-run-audit/original-scheduled/. The one-call anonymous
Qwen demo probe produced a service error and zero model responses. No new
calibration or improvement claim follows from this audit.
