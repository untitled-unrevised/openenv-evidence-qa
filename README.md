# Evidence QA — OpenEnv Arena experiment

A working experiment in teaching an agent to read evidence, obey corrections,
and submit an exact, verifiable result. Everything is synthetic. This initial
experiment has not been calibrated on the target model; no learning gain is
claimed. An Arena training reward alone would not establish improvement.

Dataset: https://huggingface.co/datasets/hieudhgdfgdfg/evidence-qa-v1

Image: `ghcr.io/untitled-unrevised/evidence-qa:v1`

There are 12 training task IDs: four invoice reconciliation instances, four
claim audits, and four subtitle audits. The task families deliberately connect
data-quality work with objective checks rather than subjective LLM judging.

The agent lists or reads in-memory files, then submits structured JSON. A
correct complete result earns 1; incomplete, wrong, duplicate, or unsupported
results earn 0. Finish and step-budget exhaustion end with 0. The server cannot
execute commands, access host files, or expose the verifier through its tools.

## Try it locally

From this directory, start the server:

```sh
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt pytest
.venv/bin/uvicorn evidence_qa.server:app --host 127.0.0.1 --port 8926
```

API documentation: http://127.0.0.1:8926/docs

Replay all 12 tasks over real WebSockets, including correct, incorrect, and
early-finish episodes:

```sh
.venv/bin/python scripts/network_check.py
```

Run verifier and isolation tests, or the Arena-pinned SDK's runtime check:

```sh
.venv/bin/python -m pytest tests -q
.venv/bin/openenv validate --url http://127.0.0.1:8926
```

Build the local container (no registry push):

```sh
docker build --platform linux/amd64 -t openenv-evidence-qa:local .
docker run --rm -p 127.0.0.1:8927:8000 openenv-evidence-qa:local
.venv/bin/python scripts/network_check.py --url http://127.0.0.1:8927
```

The network check uses an independent reference solver in `tests/`; it reads
the same observations an agent receives. Tests and reference solvers are
excluded from the image. These scripted solves check correctness of the
environment, not whether a language model can learn its tasks.

## Validation and limitations

Local validation: 255 environment tests and four calibration-adapter tests;
36 terminal WebSocket episodes on the Python server and another 36 on the local
Docker image; SDK endpoint validation; independent simultaneous sessions.
Scripted reference solves check correctness, not language-model ability.

Default instances are fixed per task ID, keeping simultaneous GRPO episodes on
the same problem. This permits memorization. Reset seeds vary the inputs but
are not structural holdouts. Binary rewards may be sparse, and ledger tasks
lack a calculation tool. This is a small reproducible first experiment rather
than a claim of a new or effective training curriculum.

`submission.template.json` intentionally has a placeholder image owner and no
dataset account. Its zero-reward finish example checks termination only.
`scripts/calibrate.py` defaults to an offline preview; executing it requires
separately configured inference access. It caps requests and stops on provider
errors, with preliminary byte-based budgets rather than the exact Arena tokenizer.
