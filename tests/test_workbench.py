import json
import os

import pytest

from evidence_qa.workbench import WorkbenchAction, WorkbenchEnvironment
from evidence_qa.tasks import TASKS
from reference import solve


@pytest.mark.parametrize("task_id", TASKS)
@pytest.mark.parametrize("seed", range(3))
def test_retry_then_correct_file_and_reset(task_id, seed):
    env = WorkbenchEnvironment()
    try:
        initial = env.reset(task_id=task_id, seed=seed)
        assert initial.steps_left == 64
        files = {name: env.step(WorkbenchAction(operation="read", path=name)).output
                 for name in initial.output.splitlines()}
        env.step(WorkbenchAction(operation="write", content="{bad json"))
        check = env.step(WorkbenchAction(operation="check"))
        assert not check.done and check.reward == 0
        assert not env.step(WorkbenchAction(operation="submit")).done
        answer = solve(task_id, files)
        env.step(WorkbenchAction(operation="write", content=json.dumps(answer)))
        check = env.step(WorkbenchAction(operation="check"))
        assert not check.done and check.reward == 0 and "passed" in check.output
        final = env.step(WorkbenchAction(operation="submit"))
        assert final.done and final.reward == 1
        assert env.step(WorkbenchAction(operation="finish")).reward == 1
        env.reset(task_id=task_id, seed=seed)
        assert not env.step(WorkbenchAction(operation="check")).done
        assert env.step(WorkbenchAction(operation="finish")).reward == 0
    finally:
        env.close()


def test_shell_refuses_host_execution():
    if os.geteuid() == 0:
        pytest.skip("This check is for the unprivileged host test runner")
    env = WorkbenchEnvironment()
    try:
        env.reset()
        result = env.step(WorkbenchAction(operation="shell", command="echo should-not-run"))
        assert result.exit_code == 126 and not result.done
    finally:
        env.close()


def test_artifact_cannot_link_outside_or_change_grader_inputs(tmp_path):
    env = WorkbenchEnvironment()
    try:
        env.reset()
        sentinel = tmp_path / "sentinel"
        sentinel.write_text("preserve")
        (env._workspace / "report.json").symlink_to(sentinel)
        result = env.step(WorkbenchAction(operation="write", content="overwrite"))
        assert "error" in result.output.lower() and sentinel.read_text() == "preserve"
        assert env.step(WorkbenchAction(operation="finish")).reward == 0
        env.reset()
        env.step(WorkbenchAction(operation="write", path="invoices.json", content="[]"))
        env.step(WorkbenchAction(operation="write", content='{"balances":{},"total_cents":0}'))
        assert env.step(WorkbenchAction(operation="finish")).reward == 0
        env.reset()
        before = env.step(WorkbenchAction(operation="list")).steps_left
        result = env.step(WorkbenchAction(operation="read", path="../grading.py"))
        assert not result.done and result.steps_left == before-1
    finally:
        env.close()


def test_budget_grades_current_artifact_and_sessions_are_separate():
    a, b = WorkbenchEnvironment(), WorkbenchEnvironment()
    try:
        initial = a.reset(task_id="ledger-1")
        b.reset(task_id="claims-1")
        files = {name: a.step(WorkbenchAction(operation="read", path=name)).output
                 for name in initial.output.splitlines()}
        a.step(WorkbenchAction(operation="write", content=json.dumps(solve("ledger-1", files))))
        while a.state.step_count < a.MAX_STEPS:
            result = a.step(WorkbenchAction(operation="list"))
        assert result.done and result.reward == 1
        assert not b.step(WorkbenchAction(operation="check")).done
        assert b.step(WorkbenchAction(operation="finish")).reward == 0
        assert a._uid != b._uid
    finally:
        a.close()
        b.close()
