from openenv.core.env_server import create_app

from .environment import EvidenceQAEnvironment
from .models import QAAction, QAObservation

app = create_app(EvidenceQAEnvironment, QAAction, QAObservation,
                 env_name="evidence_qa_env", max_concurrent_envs=8)
