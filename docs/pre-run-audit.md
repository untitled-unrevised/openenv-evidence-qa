# Pre-run curriculum audit, 2026-10-14

The second run had not been accepted or trained when this audit began. Its local
timer was stopped while preparing replacement pins; the approved id and quota
window remain unchanged. No additional Arena submission or paid inference is
authorized by this audit.

## Concrete weakness and correction

Seven deliberately flawed or weak policies were tested on 480 independently
generated grading cases each: three levels, ten seeds, sixteen cases per episode.
Four policies passed every original case despite violating the written contract.
Numerical freshness alone had not supplied enough variation in task structure.

| Weak policy | Original pass fraction | Revised pass fraction |
| --- | --- | --- |
| Use only the first amendment | 480/480 | 295/480 |
| Assume every posted credit is 50 | 480/480 | 240/480 |
| Split dialogue at the first arrow | 480/480 | 300/480 |
| Accept only choices tagged [Wait] | 480/480 | 63/480 |
| Reject touching intervals | 257/480 | 163/480 |
| Ignore interval tie breaking | 441/480 | 387/480 |
| Return cycle for every dependency graph | 120/480 | 120/480 |

Partial credit means a flawed policy can pass unaffected cases. The purpose is
to prevent full reward for those shortcuts, not to force every wrong program to
fail every individual case. Correct independent solvers still pass all cases.
These scores measure verifier coverage, not model success rates or transfer.

The generators now vary invoice statuses, counts, amendments, order and credit
amounts; dialogue topology, tags, whitespace and arrows within text; dependency
chains, branches, duplicate edges, isolated nodes, cycles, self-loops and empty
graphs; and interval touching, greedy traps, ties, negatives, zero-value jobs,
empty jobs and random general instances. Eight scenario patterns per family
appear twice in each sixteen-case final check. The family contracts and twelve
configuration ids are unchanged. This is broader development coverage, not an
independent test of transfer to unseen task families.

Visible tests previously used Python equality, which treats 1.0 as equal to 1.
They now enforce the final grader's JSON type convention. Failures are written
to failure-N.json, while the observation contains a short error and filename.
This preserves detailed evidence without consuming the token budget with full
tracebacks and large graphs on every call.

## Target-model access check

No local LM Studio or Ollama endpoint responded and no relevant configured
Qwen-provider credential was present. Inspected the public source and endpoint
metadata of akhaliq/Qwen3.8-27B at revision
a317748123bd05de6ec3375058b2c0513a79020c. Its source loads Qwen/Qwen3.8-27B in
bfloat16, supports thinking off, and exposes a public ZeroGPU endpoint.

A four-call maximum anonymous screen was prepared, supplying synthetic files and
requesting one JSON write action. Its first call returned a service error
before any model response, so the screen stopped without retries. Zero completed
model responses and no model score were obtained; no credentials were sent to
the Space and no paid provider was called. This would have been a preliminary
single-action screen, not native Arena calibration even if it had succeeded.

Local evidence: artifacts/pre-run-audit/shortcut-audit-before.json,
shortcut-audit.json, qwen-probe/results.json, preserved original scheduled pins,
and the revised container replays/publication record. The prior run record is
retained for provenance; scheduled-operation.json identifies the active pins.
