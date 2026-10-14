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

Validation evidence is under artifacts/workspace-feasibility/. Record the
published image digest, dataset revision, accepted submission/run identifiers,
and actual final evaluation after they become available. Do not infer private
scores from training rewards or call a scheduled run accepted/completed.
