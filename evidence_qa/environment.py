from uuid import uuid4

from openenv.core.env_server import Environment
from openenv.core.env_server.types import State

from .grading import grade
from .models import QAAction, QAObservation
from .tasks import TASKS, make_task


class EvidenceQAEnvironment(Environment):
    SUPPORTS_CONCURRENT_SESSIONS = True
    MAX_STEPS = 16

    def __init__(self):
        super().__init__()
        self._state = State()
        self._files = {}
        self._done = False
        self._reward = 0.0
        self._task_id = "ledger-1"

    def reset(self, seed=None, episode_id=None, task_id="ledger-1", **kwargs):
        if task_id not in TASKS:
            raise ValueError("Unknown task_id")
        instruction, self._files = make_task(task_id, seed)
        self._task_id = task_id
        self._state = State(episode_id=episode_id or str(uuid4()), step_count=0)
        self._done = False
        self._reward = 0.0
        return QAObservation(instruction=instruction, files=sorted(self._files), reward=0.0)

    def step(self, action: QAAction, timeout_s=None, **kwargs):
        if self._done:
            return QAObservation(done=True, reward=self._reward, message="Episode already ended.")
        self._state.step_count += 1
        if action.operation in ("submit", "finish"):
            self._reward = grade(TASKS[self._task_id][0], self._files, action.answer) if action.operation == "submit" else 0.0
            self._done = True
            return QAObservation(done=True, reward=self._reward, message="Episode ended.")
        if self._state.step_count >= self.MAX_STEPS:
            self._done = True
            return QAObservation(done=True, reward=0.0, message="Step budget exhausted.")
        if action.operation == "list":
            return QAObservation(files=sorted(self._files), reward=0.0)
        # Exact dictionary lookup: no filesystem, shell, network, or grader access.
        if action.path not in self._files:
            return QAObservation(message="Unknown file. Use list.", reward=0.0)
        return QAObservation(content=self._files[action.path], reward=0.0)

    @property
    def state(self):
        return self._state

    def list_splits(self):
        return ["train"]

    def list_tasks(self, split):
        if split != "train":
            raise ValueError("Unknown split")
        return [{"task_id": key} for key in TASKS]

    def num_tasks(self, split):
        return len(self.list_tasks(split))

    def get_task(self, split, index):
        return self.list_tasks(split)[index]

    def get_task_range(self, split, start=None, stop=None):
        return self.list_tasks(split)[start:stop]
