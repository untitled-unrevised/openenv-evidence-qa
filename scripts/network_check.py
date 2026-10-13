"""Replay each declared task through real WebSockets; never submits to Arena."""
import argparse
import json
import sys
from pathlib import Path

import requests
from websockets.sync.client import connect

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
from reference import solve
from evidence_qa.tasks import TASKS

parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://127.0.0.1:8926")
args = parser.parse_args()
schema = requests.get(args.url + "/schema", timeout=15).json()
results = []
for task_id in TASKS:
    with connect(args.url.replace("http", "ws", 1) + "/ws", open_timeout=15) as ws:
        def call(kind, data):
            ws.send(json.dumps({"type": kind, "data": data}))
            result = json.loads(ws.recv(timeout=15))
            if result.get("type") == "error":
                raise RuntimeError(result)
            return result["data"]
        initial = call("reset", {"task_id": task_id})
        files = {}
        for path in initial["observation"]["files"]:
            observed = call("step", {"operation": "read", "path": path})
            files[path] = observed["observation"]["content"]
        terminal = call("step", {"operation": "submit", "answer": solve(task_id, files)})
        assert terminal["done"] and terminal["reward"] == 1.0, terminal
        call("reset", {"task_id": task_id})
        wrong = call("step", {"operation": "submit", "answer": {}})
        assert wrong["done"] and wrong["reward"] == 0.0, wrong
        call("reset", {"task_id": task_id})
        finish = call("step", {"operation": "finish"})
        assert finish["done"] and finish["reward"] == 0.0, finish
        results.append({"task_id": task_id, "correct": 1.0, "wrong": 0.0, "finish": 0.0})
print(json.dumps({"url": args.url, "schema": schema, "episodes": results}, indent=2))
