"""Generate inputs only. Reference solvers live in tests, outside the image."""

import json
import random

TASKS = {f"{family}-{variant}": (family, variant)
         for family in ("ledger", "claims", "subtitles")
         for variant in range(1, 5)}


def make_task(task_id: str, seed: int | None = None) -> tuple[str, dict[str, str]]:
    family, variant = TASKS[task_id]
    # Identical task IDs yield identical instances across GRPO group sandboxes.
    # Explicit seeds enable local testing on unseen numerical instances.
    rng = random.Random(seed if seed is not None else list(TASKS).index(task_id) + 101)
    if family == "ledger":
        invoices = [{"id": f"INV-{i}", "cents": rng.randrange(5000, 70000),
                     "status": "posted" if i < 6 else "void"} for i in range(1, 8)]
        payments = [{"id": f"PAY-{i}", "invoice": f"INV-{i}", "cents": rng.randrange(100, 1500)}
                    for i in range(1, 6)]
        payments += [dict(payments[1])]  # duplicated export row, not another payment
        credits = [{"id": "CR-1", "invoice": "INV-3", "cents": rng.randrange(200, 2000),
                    "status": "posted"},
                   {"id": "CR-2", "invoice": "INV-4", "cents": 900, "status": "draft"}]
        amendments = [{"invoice": "INV-2", "revision": 2, "cents": rng.randrange(6000, 50000)},
                      {"invoice": "INV-2", "revision": 1, "cents": 20000}]
        rng.shuffle(invoices)
        rng.shuffle(payments)
        files = {"invoices.json": json.dumps(invoices), "payments.json": json.dumps(payments),
                 "credits.json": json.dumps(credits), "amendments.json": json.dumps(amendments),
                 "policy.txt": "Only posted invoices count. Use the highest amendment revision for an invoice's gross cents. Deduplicate payments by payment id. Subtract posted credits and unique payments for each posted invoice. Void invoices and draft credits do not count. Use integer cents."}
        return ('Reconcile outstanding balances. Submit {"balances": {"INV-1": integer_cents, ...}, "total_cents": integer_cents}. Include exactly the posted invoices. Inspect the policy and all data files.', files)
    if family == "claims":
        records = []
        claims = []
        for i in range(1, 7):
            n = rng.randrange(10, 100)
            records.append({"record": f"REC-{i}", "revision": 1, "value": n, "source": f"SRC-{i}"})
            mode = (i + variant) % 3
            if mode == 0:
                # A late correction invalidates a previously supported claim.
                records.append({"record": f"REC-{i}", "revision": 2, "value": n + 7,
                                "source": f"FIX-{i}"})
            claims.append({"id": f"C-{i}", "record": f"REC-{i}" if mode != 2 else f"MISSING-{i}",
                           "value": n})
        rng.shuffle(records)
        files = {"draft.json": json.dumps(claims), "sources.json": json.dumps(records),
                 "policy.txt": "For each claim, find the record with the highest revision. Label supported if values match, contradicted if they differ, or insufficient if the record does not exist. Cite that latest record's source. Use null as source only for insufficient evidence. File order is not revision order."}
        return ('Audit all draft claims. Submit {"claims": {"C-1": {"label": "supported|contradicted|insufficient", "source": "source_id or null"}, ...}}. Check policy and sources before deciding.', files)
    offset = rng.randrange(0, 10000)
    cues = [{"id": f"Q-{i}", "start_ms": offset + i * 3000,
             "end_ms": offset + i * 3000 + 1800, "text": "A short subtitle."}
            for i in range(1, 8)]
    # Vary the locations so a constant issue list cannot solve every task.
    bad, long, overlap = rng.sample(range(0, 6), 3)
    cues[bad]["end_ms"] = cues[bad]["start_ms"] - 10
    cues[long]["text"] = "x" * (43 + variant)
    cues[overlap]["end_ms"] = cues[overlap + 1]["start_ms"] + 300
    rng.shuffle(cues)
    files = {"cues.json": json.dumps(cues),
             "style.txt": "Flag nonpositive_duration when end_ms <= start_ms. Flag too_long when text contains more than 42 characters. Sort cues by start_ms. Flag overlap on the earlier cue when its end_ms exceeds the next cue's start_ms. Apply every rule independently. Submit every issue once; do not flag clean cues."}
    return ('Audit subtitle timing and length. Submit {"issues": [{"cue": "Q-id", "rule": "nonpositive_duration|too_long|overlap"}, ...]}. Inspect cues.json and style.txt.', files)
