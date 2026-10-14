---
pretty_name: Evidence Search Workbench v2
task_categories:
  - reinforcement-learning
language:
  - en
---

# Evidence Search Workbench v2

Original synthetic code-repair practice for OpenEnv Arena. Twelve configurations
cover four contracts at three size levels: invoice reconciliation, branching text
parsing, dependency ordering, and weighted interval selection. Task shapes and inputs change
on every unseeded reset. Explicit seeds reproduce an instance. No personal data
or public benchmark instances are included in training.

The agent receives solution.py with a faulty implementation, a written contract,
four public input/output examples, and executable tests.py. It can inspect files,
edit code, execute Python and shell commands, create scratch tests, and check the
original public examples. Files persist within an episode; command failures do
not terminate it. A final submit/finish ends the episode and tests the submitted
implementation on sixteen separately generated private cases. Reward is the
fraction of those cases passing, including the no-input-mutation requirement.
Private expected outputs remain in the server and are never returned by check.
Eight scenario patterns per family include simple cases and deliberate contract
boundaries: variable amendments and credit values, mixed graph shapes and tags,
arrows inside dialogue text, cycles/isolated/empty dependency graphs, and interval
touching, ties, negative values, greedy traps and empty selections. Final cases
include each scenario twice. Public tests enforce the same JSON numeric types as
the final grader, save detailed counterexamples to failure-N.json, and keep
console output concise.

The hypothesis is that practising reproducible failures, executable hypotheses,
counterexamples and code repairs can improve tool use on unfamiliar workflows.
These task families and generated cases do not establish structural transfer.
No target-model calibration, learned improvement, or leaderboard gain is claimed.
Local scripted solutions validate solvability and the tool/grading contract.

Actions: list/read/write/shell/check/submit/finish. Budget: 64 actions. Each shell
command has a ten-second wall limit and CPU/memory/output limits. Each grading
execution uses a fresh unprivileged UID and workspace; the root-only server
retains reference calculations. The outer container provides host isolation.

Source: https://github.com/untitled-unrevised/openenv-evidence-qa/tree/v2/persistent-tools

Image: ghcr.io/untitled-unrevised/evidence-qa:search-v2

SDK pin: 86a180ede21e044f7929b9a7783ad83aa67d83a3.

The tasks.jsonl and public-examples.jsonl files show seed 20261014. Runtime
generation and grading source are in source/evidence_qa/. The Arena freezes the
submitted image digest and attributes this dataset's pinned revision. Arena's
fixed GRPO training recipe is used; this is not a custom LoRA upload or a
supervised teacher-trace fine-tune.
