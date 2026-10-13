"""Small bounded calibration adapter. Default is an offline preview, never a run.

Uses the existing OpenEnv environment and HF's documented chat-completion API.
No Arena posting, publishing, submission, parallel requests, or automatic retries.
Budget accounting uses conservative UTF-8 byte bounds, not a model tokenizer.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

import requests
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evidence_qa.environment import EvidenceQAEnvironment
from evidence_qa.models import QAAction
from evidence_qa.tasks import TASKS


def parse_action(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result
    obj = json.loads(text, object_pairs_hook=pairs,
                     parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))
    if isinstance(obj, dict) and set(obj) == {"finish"} and obj["finish"] is True:
        return QAAction(operation="finish")
    if isinstance(obj, dict) and set(obj) == {"action"}:
        obj = obj["action"]
    return QAAction.model_validate(obj)


class Budget:
    def __init__(self, max_requests=48, tokens=120000, rpm=4):
        self.limit, self.tokens, self.interval = max_requests, tokens, 60 / rpm
        self.requests = self.reserved_tokens = 0
        self.last = None

    def reserve(self, tokens, clock=time.monotonic, sleep=time.sleep):
        if self.requests >= self.limit or self.reserved_tokens + tokens > self.tokens:
            raise RuntimeError("Calibration request/token cap reached")
        if self.last is not None:
            sleep(max(0, self.interval - (clock() - self.last)))
        self.last = clock()
        self.requests += 1
        self.reserved_tokens += tokens


def request_reply(url, key, model, messages, budget, output_tokens=512):
    input_bound = sum(len(m["content"].encode()) + 32 for m in messages) + 512
    budget.reserve(input_bound + output_tokens)
    response = requests.post(url, headers={"Authorization": "Bearer " + key},
                             json={"model": model, "messages": messages,
                                   "max_tokens": output_tokens, "temperature": 0.7},
                             timeout=45, allow_redirects=False)
    # Deliberately do not log provider response bodies, which may contain identifiers.
    if response.status_code != 200:
        raise RuntimeError(f"Provider HTTP {response.status_code}; stopped without retry")
    data = response.json()
    return data["choices"][0]["message"]["content"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--url", default="https://router.huggingface.co/v1/chat/completions")
    parser.add_argument("--model", default="Qwen/Qwen3.8-27B:novita")
    parser.add_argument("--max-requests", type=int, default=48)
    parser.add_argument("--max-reserved-tokens", type=int, default=120000)
    parser.add_argument("--rpm", type=float, default=4)
    parser.add_argument("--episodes", type=int, default=12)
    parser.add_argument("--output", default="artifacts/calibration-preview.json")
    args = parser.parse_args()
    if not 0 < args.rpm <= 4 or not 0 < args.max_requests <= 48 or not 0 < args.episodes <= 12:
        parser.error("Caps: 4 requests/minute, 48 requests total, 12 episodes")
    if not 0 < args.max_reserved_tokens <= 120000:
        parser.error("Token reservation must be 1..120000")
    parts = urlsplit(args.url)
    if parts.username or parts.password or parts.query or parts.fragment:
        parser.error("Do not put credentials or query parameters in the endpoint")
    if parts.scheme != "https" and not (parts.scheme == "http" and parts.hostname in ("localhost", "127.0.0.1")):
        parser.error("Use HTTPS or a loopback HTTP endpoint")
    config = {"model": args.model, "endpoint": args.url, "rpm": args.rpm,
              "request_cap": args.max_requests, "reserved_token_cap": args.max_reserved_tokens,
              "episode_cap": args.episodes, "retries": 0,
              "note": "Conservative byte budgets; not the exact Arena tokenizer or trainer prompt. Provider thinking settings are not pinned; this is preliminary calibration."}
    result = {"status": "offline_preview", "config": config, "episodes": []}
    output = Path(args.output)
    output.parent.mkdir(exist_ok=True, parents=True)
    if not args.execute:
        output.write_text(json.dumps(result, indent=2) + "\n")
        print("Saved offline preview. Zero model requests; zero Arena submissions.")
        return
    key = os.environ.get("CALIBRATION_KEY") or os.environ.get("HF_TOKEN")
    if not key:
        raise SystemExit("Missing CALIBRATION_KEY or HF_TOKEN. No requests sent.")
    budget = Budget(args.max_requests, args.max_reserved_tokens, args.rpm)
    result["status"] = "running"
    system = ('Act through the environment. Each reply must be exactly one JSON object matching the action schema, or {"finish":true}. No prose or Markdown. Action schema: ' + json.dumps(QAAction.model_json_schema()))
    try:
        for task_id in list(TASKS)[:args.episodes]:
            env = EvidenceQAEnvironment()
            observation = env.reset(task_id=task_id).model_dump()
            messages = [{"role": "system", "content": system},
                        {"role": "user", "content": json.dumps(observation)}]
            episode = {"task_id": task_id, "trace": [], "reward": None}
            result["episodes"].append(episode)
            completion_bound = 0
            for _ in range(env.MAX_STEPS):
                context_bound = sum(len(m["content"].encode()) + 32 for m in messages) + 512
                if context_bound + 512 > 8192 or completion_bound + 512 > 4096:
                    terminal = env.step(QAAction(operation="finish"))
                    episode.update(reward=terminal.reward, termination="conservative_budget")
                    break
                text = request_reply(args.url, key, args.model, messages, budget)
                if not isinstance(text, str):
                    raise RuntimeError("Provider returned no textual completion")
                messages.append({"role": "assistant", "content": text})
                completion_bound += 512
                try:
                    action = parse_action(text)
                except (ValueError, ValidationError):
                    episode.update(reward=0.0, termination="invalid_action")
                    break
                terminal = env.step(action)
                episode["trace"].append(action.model_dump())
                if terminal.done:
                    episode.update(reward=terminal.reward, termination=action.operation)
                    break
                feedback = json.dumps(terminal.model_dump())
                completion_bound += len(feedback.encode()) + 32
                messages.append({"role": "user", "content": feedback})
            output.write_text(json.dumps(result, indent=2) + "\n")
        result["status"] = "completed"
    except (RuntimeError, requests.RequestException, KeyError, TypeError, ValueError) as error:
        result["status"] = "stopped"
        result["stop_type"] = type(error).__name__
        print("Calibration stopped; inspect local artifact. No automatic retry.")
    finally:
        result["requests"] = budget.requests
        result["reserved_tokens"] = budget.reserved_tokens
        output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Status: {result['status']}; requests: {budget.requests}; reserved tokens: {budget.reserved_tokens}")


if __name__ == "__main__":
    main()
