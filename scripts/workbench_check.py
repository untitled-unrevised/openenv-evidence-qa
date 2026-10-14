"""Exercise real v2 shell tools, retries, artifacts and session isolation.

This uses scripted reference policies, not language-model inference.
"""
import argparse
import json
import sys
from pathlib import Path

import requests
from websockets.sync.client import connect

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from evidence_qa.tasks import TASKS

parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://127.0.0.1:8929")
args = parser.parse_args()
schema = requests.get(args.url+"/schema", timeout=15).json()
results = []


def call(ws, kind, data):
    ws.send(json.dumps({"type": kind, "data": data}))
    result = json.loads(ws.recv(timeout=20))
    if result.get("type") == "error":
        raise RuntimeError(result)
    return result["data"]


ws_url = args.url.replace("http", "ws", 1)+"/ws"
for task_id in TASKS:
    with connect(ws_url, open_timeout=15) as ws:
        initial = call(ws, "reset", {"task_id": task_id})
        names = initial["observation"]["output"].splitlines()
        call(ws, "step", {"operation": "write", "content": "{bad json"})
        assert not call(ws, "step", {"operation": "submit"})["done"]
        failed = call(ws, "step", {"operation": "shell", "command": "python missing.py"})
        assert failed["observation"]["exit_code"] != 0 and not failed["done"]
        # Deliver this policy through the same write+shell tools used by the model.
        source = (root/"tests/reference.py").read_text()
        source += "\nfrom pathlib import Path\n"
        source += f"files={{name:Path(name).read_text() for name in {names!r}}}\n"
        source += f"Path('report.json').write_text(json.dumps(solve({task_id!r},files)))\n"
        call(ws, "step", {"operation": "write", "path": "solve.py", "content": source})
        ran = call(ws, "step", {"operation": "shell", "command": "python solve.py"})
        assert ran["observation"]["exit_code"] == 0, ran
        checked = call(ws, "step", {"operation": "check"})
        assert not checked["done"] and "passed" in checked["observation"]["output"], checked
        final = call(ws, "step", {"operation": "submit"})
        assert final["done"] and final["reward"] == 1, final
        call(ws, "reset", {"task_id": task_id})
        assert call(ws, "step", {"operation": "finish"})["reward"] == 0
        results.append({"task_id": task_id, "wrong_submit_retry": True,
                        "failed_command_recovery": True, "executed_solution": 1,
                        "reset_reward": 0})

with connect(ws_url) as a, connect(ws_url) as b:
    call(a, "reset", {"task_id": "ledger-1"})
    call(b, "reset", {"task_id": "claims-1"})
    uid_a = call(a, "step", {"operation": "shell", "command": "id -u"})
    uid_b = call(b, "step", {"operation": "shell", "command": "id -u"})
    assert uid_a["observation"]["output"].strip() != uid_b["observation"]["output"].strip()
    forbidden = call(a, "step", {"operation": "shell", "command": "cat /app/evidence_qa/grading.py"})
    assert forbidden["observation"]["exit_code"] != 0
    rename = call(a, "step", {"operation": "shell", "command": 'mv "$HOME" "${HOME}.moved"'})
    assert rename["observation"]["exit_code"] != 0
    call(a, "step", {"operation": "write", "path": "marker", "content": "session a"})
    missing = call(b, "step", {"operation": "read", "path": "marker"})
    assert "error" in missing["observation"]["output"].lower()
    timed = call(a, "step", {"operation": "shell", "command": "sleep 20"})
    assert timed["observation"]["exit_code"] == 124 and not timed["done"]
    assert call(a, "step", {"operation": "read", "path": "marker"})["observation"]["output"] == "session a"

print(json.dumps({"url": args.url, "schema": schema, "tasks": results,
                  "different_session_uids": True, "grader_access_denied": True,
                  "workspace_rename_denied": True, "timeout_recovery": True}, indent=2))
