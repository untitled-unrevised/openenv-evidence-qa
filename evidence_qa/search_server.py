from openenv.core.env_server import create_app
from .workbench import WorkbenchAction, WorkbenchObservation
from .search_workbench import SearchWorkbenchEnvironment

app=create_app(SearchWorkbenchEnvironment,WorkbenchAction,WorkbenchObservation,
               env_name='evidence_search_workbench',max_concurrent_envs=8)
