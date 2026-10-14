from openenv.core.env_server import create_app

from .workbench import WorkbenchAction, WorkbenchEnvironment, WorkbenchObservation

app = create_app(WorkbenchEnvironment, WorkbenchAction, WorkbenchObservation,
                 env_name="evidence_workbench_env", max_concurrent_envs=8)
