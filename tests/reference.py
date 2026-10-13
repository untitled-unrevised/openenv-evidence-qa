"""Independent reference calculations used only for local verifier checks."""

import json


def solve(task_id, files):
    if task_id.startswith("ledger"):
        rows = json.loads(files["invoices.json"])
        changes = sorted(json.loads(files["amendments.json"]), key=lambda a: a["revision"])
        gross = {r["id"]: r["cents"] for r in rows if r["status"] == "posted"}
        for change in changes:
            if change["invoice"] in gross:
                gross[change["invoice"]] = change["cents"]
        seen = set()
        for payment in json.loads(files["payments.json"]):
            if payment["id"] not in seen and payment["invoice"] in gross:
                gross[payment["invoice"]] -= payment["cents"]
            seen.add(payment["id"])
        for credit in json.loads(files["credits.json"]):
            if credit["status"] == "posted" and credit["invoice"] in gross:
                gross[credit["invoice"]] -= credit["cents"]
        return {"balances": gross, "total_cents": sum(gross.values())}
    if task_id.startswith("claims"):
        latest = {}
        for row in sorted(json.loads(files["sources.json"]), key=lambda r: r["revision"]):
            latest[row["record"]] = row
        answer = {}
        for claim in json.loads(files["draft.json"]):
            record = latest.get(claim["record"])
            label = "insufficient" if record is None else "supported" if record["value"] == claim["value"] else "contradicted"
            answer[claim["id"]] = {"label": label, "source": record["source"] if record else None}
        return {"claims": answer}
    rows = json.loads(files["cues.json"])
    issues = []
    for cue in rows:
        if cue["end_ms"] - cue["start_ms"] <= 0:
            issues.append({"cue": cue["id"], "rule": "nonpositive_duration"})
        if len(cue["text"]) >= 43:
            issues.append({"cue": cue["id"], "rule": "too_long"})
        later = [r["start_ms"] for r in rows if r["start_ms"] > cue["start_ms"]]
        if later and cue["end_ms"] > min(later):
            issues.append({"cue": cue["id"], "rule": "overlap"})
    return {"issues": issues}
