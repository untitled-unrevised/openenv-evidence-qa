# Evidence QA v1 — Arena run

Submission: `evidence-qa-v1`

Run: `5e9d18e3bcf706ac9c5c0fc8`

Dashboard: https://openenvarena-training.hf.space/?project=hieudhgdfgdfg&runs=5e9d18e3bcf706ac9c5c0fc8

Source revision at publication: `89a114b`

Image: `ghcr.io/untitled-unrevised/evidence-qa@sha256:17d46aa02981a896f07255818dd7f34c495bf28198b1e8eee12eb8cd90b2b9b3`

Dataset: https://huggingface.co/datasets/hieudhgdfgdfg/evidence-qa-v1/tree/d551852b723ade297d8555d497a4234b59cbb55c

## Verified before submission

The published linux/amd64 image was pulled using an empty Docker credential
configuration. The SDK runtime checks passed (6/6) and all 36 terminal network
episodes passed: correct answer, wrong answer and early finish for each of the
12 task IDs. Source verifier and calibration-adapter tests passed (259 tests).

## Admission

Arena returned HTTP 202 with `simulated: false`, resolved the exact image digest,
and pinned the dataset revision. All static checks passed. Its sandbox admission
then passed, the submission became `validated`, and its daily slot became `used`.
The run received Slurm job 1498 and a 14400-second budget on one GPU.

## Final evaluation

The real run completed 308 optimizer updates without a reported run error.
Arena's heldout-v2 evaluation returned **3/40 solved (7.5%)**, versus the
untrained reference's **4/40 (10%)**: one fewer solve, or -2.5 percentage points.

Industrial: 2/5, unchanged from the reference. Office: 1/5, versus the
reference's 2/5. Software, science, finance, math, security and media: 0/5 each.
This single evaluation demonstrates no gain; it is too small to attribute the
one-task difference reliably to training rather than evaluation variation.

On 2026-10-14, the live leaderboard listed the account at position24 of28,
with ten accounts tied at7.5%. The leading account's domain-best aggregate
was20%. Positions and the leader can change.

The final reward-curve fetch timed out on2026-10-14, so no final training-reward
trend is claimed. Earlier observations (25 logged steps) had14 zero-variance
groups and clipped_ratio=1.0; the clipping metric's interpretation remains
unresolved. Neither observation establishes the cause of the evaluation result.

The next accepted-submission slot opens2026-10-14 at22:55:39 UTC+7, according
to the returned account slot. No second submission has been made.

This is an uncalibrated initial experiment. Fixed training instances, binary
rewards, limited task diversity and lack of a calculation tool are known limits.
Training reward will not by itself demonstrate transfer to the private suite.
