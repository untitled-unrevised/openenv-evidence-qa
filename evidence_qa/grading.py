"""Deterministic verifier; no grader data or source exposed by actions."""

import json
from typing import Any


def grade(family: str, files: dict[str, str], answer: dict[str, Any]) -> float:
    try:
        if family == "ledger":
            invoices = json.loads(files["invoices.json"])
            amendments = json.loads(files["amendments.json"])
            payments = {p["id"]: p for p in json.loads(files["payments.json"])}
            credits = json.loads(files["credits.json"])
            balances = {}
            for inv in invoices:
                if inv["status"] != "posted":
                    continue
                changes = [a for a in amendments if a["invoice"] == inv["id"]]
                gross = max(changes, key=lambda a: a["revision"])["cents"] if changes else inv["cents"]
                paid = sum(p["cents"] for p in payments.values() if p["invoice"] == inv["id"])
                credit = sum(c["cents"] for c in credits if c["invoice"] == inv["id"] and c["status"] == "posted")
                balances[inv["id"]] = gross - paid - credit
            # Reject bools, floats, extras, missing values, and guessed totals.
            got = answer.get("balances", {})
            if set(answer) != {"balances", "total_cents"} or not isinstance(got, dict):
                return 0.0
            if set(got) != set(balances) or any(type(v) is not int for v in got.values()):
                return 0.0
            if type(answer["total_cents"]) is not int:
                return 0.0
            return float(got == balances and answer["total_cents"] == sum(balances.values()))
        if family == "claims":
            records = json.loads(files["sources.json"])
            expected = {}
            for claim in json.loads(files["draft.json"]):
                candidates = [r for r in records if r["record"] == claim["record"]]
                if not candidates:
                    expected[claim["id"]] = {"label": "insufficient", "source": None}
                else:
                    latest = max(candidates, key=lambda r: r["revision"])
                    expected[claim["id"]] = {"label": "supported" if latest["value"] == claim["value"] else "contradicted", "source": latest["source"]}
            return float(answer == {"claims": expected})
        cues = sorted(json.loads(files["cues.json"]), key=lambda c: c["start_ms"])
        expected = set()
        for i, cue in enumerate(cues):
            if cue["end_ms"] <= cue["start_ms"]:
                expected.add((cue["id"], "nonpositive_duration"))
            if len(cue["text"]) > 42:
                expected.add((cue["id"], "too_long"))
            if i + 1 < len(cues) and cue["end_ms"] > cues[i + 1]["start_ms"]:
                expected.add((cue["id"], "overlap"))
        if set(answer) != {"issues"} or not isinstance(answer["issues"], list):
            return 0.0
        issues = answer["issues"]
        if any(not isinstance(i, dict) or set(i) != {"cue", "rule"} for i in issues):
            return 0.0
        got = {(i["cue"], i["rule"]) for i in issues}
        return float(got == expected and len(got) == len(issues))
    except (KeyError, TypeError, ValueError):
        return 0.0
