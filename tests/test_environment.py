import copy
import json

import pytest

from evidence_qa.environment import EvidenceQAEnvironment
from evidence_qa.models import QAAction
from evidence_qa.tasks import TASKS
from reference import solve


def observe(env, task_id, seed=None):
    obs = env.reset(task_id=task_id, seed=seed)
    files = {path: env.step(QAAction(operation="read", path=path)).content for path in obs.files}
    return files


@pytest.mark.parametrize("task_id", TASKS)
@pytest.mark.parametrize("seed", range(20))
def test_correct_and_incorrect_answers(task_id, seed):
    env = EvidenceQAEnvironment()
    files = observe(env, task_id, seed)
    answer = solve(task_id, files)
    result = env.step(QAAction(operation="submit", answer=answer))
    assert result.done and result.reward == 1.0
    assert env.step(QAAction(operation="submit", answer={})).reward == 1.0
    observe(env, task_id, seed)
    assert env.step(QAAction(operation="submit", answer={})).reward == 0.0
    observe(env, task_id, seed)
    wrong = copy.deepcopy(answer)
    if task_id.startswith("ledger"):
        wrong["total_cents"] += 1
    elif task_id.startswith("claims"):
        wrong["claims"]["C-1"]["source"] = "invented"
    else:
        wrong["issues"].append(wrong["issues"][0])
    assert env.step(QAAction(operation="submit", answer=wrong)).reward == 0.0


@pytest.mark.parametrize("task_id", TASKS)
def test_finish_budget_and_no_grader_access(task_id):
    env = EvidenceQAEnvironment()
    env.reset(task_id=task_id)
    for path in ("../grading.py", "/etc/passwd", "answer.json"):
        obs = env.step(QAAction(operation="read", path=path))
        assert obs.content == "" and "Unknown file" in obs.message
    result = env.step(QAAction(operation="finish"))
    assert result.done and result.reward == 0.0
    env.reset(task_id=task_id)
    for _ in range(env.MAX_STEPS):
        result = env.step(QAAction(operation="list"))
    assert result.done and result.reward == 0.0


def test_sessions_are_isolated_and_default_instances_match():
    a, b = EvidenceQAEnvironment(), EvidenceQAEnvironment()
    first = observe(a, "claims-1")
    assert observe(b, "claims-1") == first
    a.step(QAAction(operation="submit", answer=solve("claims-1", first)))
    assert not b.step(QAAction(operation="list")).done
    observe(b, "ledger-2")
    assert a.state.episode_id != b.state.episode_id
    assert a.step(QAAction(operation="list")).reward == 1.0


def test_ledger_requires_every_balance_and_exact_integer_types():
    env = EvidenceQAEnvironment()
    files = observe(env, "ledger-1")
    answer = solve("ledger-1", files)
    answer["balances"]["INV-1"] += 1
    answer["balances"]["INV-2"] -= 1
    assert env.step(QAAction(operation="submit", answer=answer)).reward == 0
    files = observe(env, "ledger-1")
    answer = solve("ledger-1", files)
    answer["total_cents"] = float(answer["total_cents"])
    assert env.step(QAAction(operation="submit", answer=answer)).reward == 0


def test_unknown_task_rejected():
    with pytest.raises(ValueError):
        EvidenceQAEnvironment().reset(task_id="missing")
