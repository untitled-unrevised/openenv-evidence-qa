from typing import Any, Literal

from openenv.core.env_server.types import Action, Observation
from pydantic import Field


class QAAction(Action):
    operation: Literal["list", "read", "submit", "finish"]
    path: str = ""
    answer: dict[str, Any] = Field(default_factory=dict)


class QAObservation(Observation):
    instruction: str = ""
    files: list[str] = Field(default_factory=list)
    content: str = ""
    message: str = ""
