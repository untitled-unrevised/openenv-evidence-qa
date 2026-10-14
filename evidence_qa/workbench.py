"""V2 draft: persistent files and unprivileged shell tools inside a container.

Uses the existing OpenEnv contract and v1 tasks/verifier. Shell execution is
refused outside a root-run container. Each session gets a separate UID and
0700 workspace. This relies on the outer container for host isolation.
"""
import json
import os
import signal
import stat
import subprocess
import tempfile
import threading
from itertools import count
from pathlib import Path
from uuid import uuid4

from openenv.core.env_server import Environment
from openenv.core.env_server.types import Action, Observation, State
from pydantic import Field
from typing import Literal

from .grading import grade
from .tasks import TASKS, make_task

_UIDS = count(20000)
_UID_LOCK = threading.Lock()


class WorkbenchAction(Action):
    operation: Literal["list", "read", "write", "shell", "check", "submit", "finish"]
    path: str = "report.json"
    content: str = ""
    command: str = ""


class WorkbenchObservation(Observation):
    instruction: str = ""
    output: str = ""
    exit_code: int | None = None
    steps_left: int = 0


class WorkbenchEnvironment(Environment):
    SUPPORTS_CONCURRENT_SESSIONS = True
    MAX_STEPS = 64
    OUTPUT_LIMIT = 3000

    def __init__(self):
        super().__init__()
        self._state = State()
        self._temporary = None
        self._workspace = None
        self._files = {}
        self._task_id = "ledger-1"
        self._done = False
        self._reward = 0.0
        self._uid = None

    def _observation(self, output="", instruction="", exit_code=None):
        if len(output) > self.OUTPUT_LIMIT:
            output = output[:self.OUTPUT_LIMIT] + "\n[output truncated; narrow the command or save results to a file]"
        return WorkbenchObservation(output=output, instruction=instruction,
                                    exit_code=exit_code, done=self._done,
                                    reward=self._reward,
                                    steps_left=max(0, self.MAX_STEPS-self._state.step_count))

    def reset(self, seed=None, episode_id=None, task_id="ledger-1", **kwargs):
        if task_id not in TASKS:
            raise ValueError("Unknown task_id")
        self.close()
        instruction, self._files = make_task(task_id, seed)
        self._task_id = task_id
        self._state = State(episode_id=episode_id or str(uuid4()), step_count=0)
        self._done = False
        self._reward = 0.0
        self._temporary = tempfile.TemporaryDirectory(prefix="evidence-wb-")
        # The parent stays server-owned so an agent cannot rename its work
        # directory and replace the root path with a symlink.
        parent = Path(self._temporary.name)
        parent.chmod(0o711)
        self._workspace = parent / "work"
        self._workspace.mkdir(mode=0o700)
        with _UID_LOCK:
            self._uid = next(_UIDS)
        if os.geteuid() == 0:
            os.chown(self._workspace, self._uid, self._uid)
        self._workspace.chmod(0o700)
        for name, content in self._files.items():
            self._write(name, content)
        brief = (instruction + "\nProduce report.json with that answer schema. "
                 "Tools: list; read(path); write(path,content); shell(command); check; submit; finish. "
                 "shell runs sh commands, including python and git, in your persistent workspace. "
                 "Python stdlib includes json, csv, sqlite3, decimal, math and unittest. "
                 "Use scripts to calculate and verify. Files persist between calls; shell variables do not. "
                 "check validates report.json without ending the episode. A failed submit also stays open: "
                 "inspect, repair and retry. Successful submit ends with reward1. "
                 "finish ends immediately and grades the current report. "
                 "You have64 actions; each shell call lasts at most10 seconds. "
                 "Keep outputs short to preserve the token budget.")
        return self._observation(instruction=brief, output="\n".join(sorted(self._files)))

    def _name(self, path):
        # Files are flat; dir_fd + O_NOFOLLOW also prevents final-component races.
        if not path or path in (".", "..") or "/" in path or "\\" in path or "\x00" in path:
            raise ValueError("Use a plain filename in this workspace")
        return path

    def _write(self, path, content):
        name = self._name(path)
        if len(content.encode()) > 65536:
            raise ValueError("File content exceeds64 KiB")
        directory = os.open(self._workspace, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
                         0o600, dir_fd=directory)
            try:
                info = os.fstat(fd)
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                    raise ValueError("Expected an ordinary file with one hard link")
                os.ftruncate(fd, 0)
                if os.geteuid() == 0:
                    os.fchown(fd, self._uid, self._uid)
                with os.fdopen(fd, "w", closefd=False) as out:
                    out.write(content)
            finally:
                os.close(fd)
        finally:
            os.close(directory)

    def _read(self, path):
        directory = os.open(self._workspace, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            fd = os.open(self._name(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                         dir_fd=directory)
            try:
                info = os.fstat(fd)
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 65536:
                    raise ValueError("Expected an ordinary file of at most64 KiB")
                with os.fdopen(fd, "r", closefd=False) as src:
                    return src.read(65537)
            finally:
                os.close(fd)
        finally:
            os.close(directory)

    def _check(self):
        try:
            answer = json.loads(self._read("report.json"))
            if not isinstance(answer, dict):
                return 0.0, "report.json must contain a JSON object"
            score = grade(TASKS[self._task_id][0], self._files, answer)
            return score, "All checks passed" if score == 1 else "Report incomplete or incorrect; recheck the original inputs and policy"
        except (OSError, ValueError, UnicodeError):
            return 0.0, "report.json is missing, unreadable or invalid JSON"

    def _shell(self, command, timeout=10):
        if not (os.geteuid() == 0 and Path("/.dockerenv").exists()
                and os.environ.get("EVIDENCE_WORKBENCH_CONTAINER") == "1"):
            return 126, "Shell execution requires the dedicated Workbench container"
        if len(command.encode()) > 16384:
            return 126, "Command exceeds16 KiB; write a script and execute it"
        env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(self._workspace),
               "TMPDIR": str(self._workspace), "LANG": "C.UTF-8",
               "PYTHONDONTWRITEBYTECODE": "1"}
        process = subprocess.Popen(
            ["/usr/bin/prlimit", "--cpu=5", "--as=536870912", "--fsize=1048576",
             "--nproc=32", "--nofile=64", "--", "/bin/sh", "-c", command],
            cwd=self._workspace, env=env, user=self._uid, group=self._uid,
            extra_groups=[], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, start_new_session=True)
        chunks = []
        def drain():
            kept = 0
            while chunk := process.stdout.read(8192):
                if kept < 65536:
                    part = chunk[:65536-kept]
                    chunks.append(part)
                    kept += len(part)
        reader = threading.Thread(target=drain, daemon=True)
        reader.start()
        timed_out = False
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
            reader.join(2)
            process.stdout.close()
        output = b"".join(chunks).decode(errors="replace")
        if timed_out:
            output += "\nCommand timed out; files are preserved. Inspect and retry."
        return 124 if timed_out else process.returncode, output

    def step(self, action: WorkbenchAction, timeout_s=None, **kwargs):
        if self._workspace is None:
            raise ValueError("Reset the environment first")
        if self._done:
            return self._observation("Episode already ended")
        self._state.step_count += 1
        output, code = "", None
        try:
            if action.operation == "list":
                output = "\n".join(sorted(p.name for p in self._workspace.iterdir()))
            elif action.operation == "read":
                output = self._read(action.path)
            elif action.operation == "write":
                self._write(action.path, action.content)
                output = "File written"
            elif action.operation == "shell":
                code, output = self._shell(action.command)
            else:
                score, output = self._check()
                if action.operation == "finish" or (action.operation == "submit" and score == 1):
                    self._reward, self._done = score, True
        except (ValueError, OSError, UnicodeError) as error:
            output = f"Tool error: {type(error).__name__}; inspect inputs and retry"
        if self._state.step_count >= self.MAX_STEPS and not self._done:
            self._reward, _ = self._check()
            self._done = True
            output += "\nAction budget exhausted; current report graded"
        return self._observation(output=output, exit_code=code)

    @property
    def state(self):
        return self._state

    def close(self):
        if self._temporary is not None:
            self._temporary.cleanup()
            self._temporary = None
        self._workspace = None
