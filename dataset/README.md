---
pretty_name: Evidence QA
task_categories:
  - reinforcement-learning
language:
  - en
---

# Evidence QA

Twelve synthetic task instances for evidence-based data quality: invoice
reconciliation, claim audits against versioned source records, and subtitle
timing and length audits. No personal data or third-party benchmark examples
are used. `tasks.jsonl` contains task IDs, instructions, and the documents the
agent can inspect, without reference answers.

Actions are list, read, submit, and finish. Rewards are binary: 1 only for the
complete correct result, otherwise 0. Claim audits require the latest source
citations; ledger audits require all posted balances and a correct total;
subtitle audits require the exact unique set of issues. A maximum of 16 actions
ends the episode. This dataset has not been evaluated for model improvement.

Default task instances are fixed per ID so GRPO groups compare the same problem.
Explicit reset seeds produce additional numerical/input variations for local
testing. These variations are not structurally distinct holdouts. The four
variants within each family are not four novel workflow types.

Source: https://github.com/untitled-unrevised/openenv-evidence-qa

Container: ghcr.io/untitled-unrevised/evidence-qa:v1

OpenEnv is pinned to revision 86a180ede21e044f7929b9a7783ad83aa67d83a3.
This is an initial environment experiment; no learned improvement is claimed.
