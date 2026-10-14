"""Actual network replay of original search tasks; scripted, not model trials."""
import argparse
import json
import sys
from pathlib import Path

import requests
from websockets.sync.client import connect

root=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(root),str(root/'tests')]
from evidence_qa.search_curriculum import SEARCH_TASKS
from search_solutions import SOLUTIONS

parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:8930')
parser.add_argument('--seed',type=int,default=2718)
args=parser.parse_args()
ws_url=args.url.replace('http','ws',1)+'/ws'
def call(ws,kind,data):
    ws.send(json.dumps({'type':kind,'data':data}));r=json.loads(ws.recv(timeout=25))
    if r.get('type')=='error':raise RuntimeError(r)
    return r['data']

results=[]
for task_id,(family,level) in SEARCH_TASKS.items():
    with connect(ws_url) as ws:
        initial=call(ws,'reset',{'task_id':task_id,'seed':args.seed})
        baseline=call(ws,'step',{'operation':'check'})
        assert not baseline['done'] and baseline['reward']==0
        failure=call(ws,'step',{'operation':'shell','command':'python tests.py'})
        assert not failure['done']
        call(ws,'step',{'operation':'write','path':'solution.py','content':SOLUTIONS[family]})
        tests=call(ws,'step',{'operation':'shell','command':'python tests.py'})
        assert tests['observation']['exit_code']==0,tests
        public=call(ws,'step',{'operation':'check'})
        assert '4/4' in public['observation']['output'] and not public['done'],public
        final=call(ws,'step',{'operation':'submit'})
        assert final['done'] and final['reward']==1,final
        call(ws,'reset',{'task_id':task_id,'seed':args.seed})
        call(ws,'step',{'operation':'write','path':'solution.py','content':'def solve(data): return {}\n'})
        call(ws,'step',{'operation':'write','path':'tests.py','content':'print("fake pass")\n'})
        bad=call(ws,'step',{'operation':'check'})
        assert '0/4' in bad['observation']['output'],bad
        final_bad=call(ws,'step',{'operation':'submit'})
        assert final_bad['done'] and final_bad['reward']==0,final_bad
        results.append({'task_id':task_id,'starter_public':baseline['observation']['output'],
                        'repaired_public':public['observation']['output'],'private_reward':final['reward'],
                        'tampered_tests_private_reward':final_bad['reward']})

with connect(ws_url) as a,connect(ws_url) as b:
    call(a,'reset',{'task_id':'reconcile-1'});call(b,'reset',{'task_id':'dialogue-1'})
    ua=call(a,'step',{'operation':'shell','command':'id -u'})
    ub=call(b,'step',{'operation':'shell','command':'id -u'})
    assert ua['observation']['output']!=ub['observation']['output']
    forbidden=call(a,'step',{'operation':'shell','command':'cat /app/evidence_qa/search_curriculum.py'})
    assert forbidden['observation']['exit_code']!=0
    call(a,'step',{'operation':'write','path':'solution.py','content':SOLUTIONS['reconcile']})
    for i in range(62):final=call(a,'step',{'operation':'list'})
    assert final['done'] and final['reward']==1,final

print(json.dumps({'seed':args.seed,'tasks':results,'private_source_denied':True,'session_isolation':True,
                  'budget_uses_private_grade':True,'model_trials':0,
                  'schema':requests.get(args.url+'/schema',timeout=15).json()},indent=2))
