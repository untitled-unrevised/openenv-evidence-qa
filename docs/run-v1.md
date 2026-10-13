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

At this record's creation, the run was loading with policy_version=0 and no
evaluation result. The dashboard is the live reference for subsequent progress.
No learning gain, final private score, or leaderboard rank is claimed here.

This is an uncalibrated initial experiment. Fixed training instances, binary
rewards, limited task diversity and lack of a calculation tool are known limits.
Training reward will not by itself demonstrate transfer to the private suite.
