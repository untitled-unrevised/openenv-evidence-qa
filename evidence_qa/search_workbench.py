"""Code repair with public counterexamples and one terminal private evaluation."""
import json
import os
import tempfile
from pathlib import Path

from .workbench import WorkbenchEnvironment, _UIDS, _UID_LOCK
from .search_curriculum import SEARCH_TASKS, make_search_task


def same_json(actual, expected):
    # Python considers True == 1 and 1.0 == 1; the artifact contract does not.
    return json.dumps(actual,sort_keys=True,allow_nan=False,separators=(',',':')) == json.dumps(
        expected,sort_keys=True,allow_nan=False,separators=(',',':'))


class SearchWorkbenchEnvironment(WorkbenchEnvironment):
    def reset(self, seed=None, episode_id=None, task_id='reconcile-1', **kwargs):
        if task_id not in SEARCH_TASKS:raise ValueError('Unknown task_id')
        super().reset(seed=seed,episode_id=episode_id,task_id='ledger-1')
        for name in self._files:(self._workspace/name).unlink()
        instruction,self._files,self._public,self._private=make_search_task(task_id,seed)
        self._task_id=task_id
        for name,content in self._files.items():self._write(name,content)
        return self._observation(instruction=instruction,output='\n'.join(sorted(self._files)))

    def _evaluate(self, cases):
        try:source=self._read('solution.py')
        except (OSError,ValueError,UnicodeError):return 0.0,'solution.py missing or unreadable'
        # Never import submitted code into the privileged server. A fresh UID,
        # workspace and process handle each evaluation. Expected answers stay
        # in server memory; the worker only receives input cases.
        workspace,uid=self._workspace,self._uid
        runner="""import copy,json,runpy
namespace=runpy.run_path('solution.py'); fn=namespace['solve']
results=[]
for data in json.load(open('inputs.json')):
    before=copy.deepcopy(data)
    try:
        result=fn(data)
        results.append({'result':result,'mutated':data!=before})
    except Exception:
        results.append({'error':True})
print(json.dumps(results,allow_nan=False))
"""
        with tempfile.TemporaryDirectory(prefix='evidence-eval-') as directory:
            parent=Path(directory);parent.chmod(0o711)
            evaluation=parent/'work';evaluation.mkdir(mode=0o700)
            with _UID_LOCK:evaluation_uid=next(_UIDS)
            if os.geteuid()==0:os.chown(evaluation,evaluation_uid,evaluation_uid)
            for name,content in [('solution.py',source),('runner.py',runner),
                                 ('inputs.json',json.dumps([d for d,e in cases]))]:
                path=evaluation/name;path.write_text(content);path.chmod(0o644)
            try:
                self._workspace,self._uid=evaluation,evaluation_uid
                code,output=self._shell('python -I runner.py',timeout=8)
            finally:self._workspace,self._uid=workspace,uid
        if code!=0:return 0.0,'Execution failed or exceeded resource limits'
        try:
            actual=json.loads(output)
            if not isinstance(actual,list) or len(actual)!=len(cases):raise ValueError()
            passed=[isinstance(a,dict) and 'result' in a and not a.get('mutated',True)
                    and same_json(a['result'],expected) for a,(data,expected) in zip(actual,cases)]
        except (ValueError,TypeError,KeyError):return 0.0,'Invalid result serialization'
        count=sum(passed)
        return count/len(cases),f'{count}/{len(cases)} cases passed'

    def _check(self):
        return self._evaluate([(e['input'],e['expected']) for e in self._public])

    def step(self,action,timeout_s=None,**kwargs):
        if self._workspace is None:raise ValueError('Reset first')
        if self._done:return self._observation('Episode already ended')
        if action.operation in ('submit','finish'):
            self._state.step_count+=1
            self._reward,_=self._evaluate(self._private)
            self._done=True
            return self._observation('Terminal private evaluation complete')
        # The base loop's public check cannot become the terminal reward on
        # action-budget exhaustion. Final grading always uses private cases.
        if self._state.step_count>=self.MAX_STEPS-1:
            self._state.step_count+=1
            self._reward,_=self._evaluate(self._private)
            self._done=True
            return self._observation('Action budget exhausted; private cases graded')
        return super().step(action,timeout_s=timeout_s,**kwargs)
