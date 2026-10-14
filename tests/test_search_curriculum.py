import copy
import json
import subprocess
import sys

import pytest

from evidence_qa.search_curriculum import SEARCH_TASKS, make_search_task, reference
from search_solutions import SOLUTIONS
from evidence_qa.search_workbench import same_json


@pytest.mark.parametrize('task_id',SEARCH_TASKS)
@pytest.mark.parametrize('seed',[7,101,99991])
def test_independent_solutions_on_fresh_public_and_private(task_id,seed):
    instruction,files,public,private=make_search_task(task_id,seed)
    scope={};exec(SOLUTIONS[SEARCH_TASKS[task_id][0]],scope)
    for data,expected in [(e['input'],e['expected']) for e in public]+private:
        original=copy.deepcopy(data)
        assert scope['solve'](data)==expected
        assert data==original
    assert json.loads(files['examples.json'])==public
    assert 'private' not in files and len(private)==16


def test_semantic_boundaries():
    assert reference('dependencies',{'nodes':['z','a'],'edges':[]})=={'order':['a','z']}
    assert reference('dependencies',{'nodes':['a','b'],'edges':[['a','b'],['b','a']]})=={'order':None}
    assert reference('intervals',{'jobs':[{'id':'z','start':0,'end':1,'value':-1}]})=={'ids':[],'value':0}
    assert reference('intervals',{'jobs':[{'id':'a','start':0,'end':1,'value':2},{'id':'b','start':1,'end':2,'value':3}]})=={'ids':['a','b'],'value':5}
    assert reference('intervals',{'jobs':[{'id':'z','start':0,'end':2,'value':5},{'id':'a','start':0,'end':2,'value':5}]})=={'ids':['a'],'value':5}


def test_fresh_instances_and_reproducible_explicit_seed():
    for task_id in SEARCH_TASKS:
        assert make_search_task(task_id,17)==make_search_task(task_id,17)
        assert make_search_task(task_id)[1]!=make_search_task(task_id)[1]


def test_integer_outputs_and_object_order_are_graded_correctly():
    assert same_json({'a':1,'b':2},{'b':2,'a':1})
    assert not same_json({'value':True},{'value':1})
    assert not same_json({'value':1.0},{'value':1})


@pytest.mark.parametrize('name,family,source',[
    ('first amendment', 'reconcile', SOLUTIONS['reconcile'].replace(
        "sorted(data['amendments'],key=lambda a:a['revision'])", "data['amendments'][:1]")),
    ('fixed credit', 'reconcile', SOLUTIONS['reconcile'].replace(
        "balances[c['invoice']]-=c['cents']", "balances[c['invoice']]-=50")),
    ('first arrow', 'dialogue', SOLUTIONS['dialogue'].replace("s.rsplit('->',1)","s.split('->',1)")),
    ('required tag', 'dialogue', SOLUTIONS['dialogue'].replace(
        "text=m.group(1)","text=m.group(1) if m.group(1).startswith('[Wait]') else ''")),
    ('touching forbidden','intervals',SOLUTIONS['intervals'].replace("a['end']>b['start']","a['end']>=b['start']")),
    ('ignore tie','intervals',SOLUTIONS['intervals'].replace(
        "if val>best_value or (val==best_value and ids<best_ids)","if val>best_value")),
])
def test_generated_cases_reject_contract_shortcuts(name,family,source):
    scope={};exec(source,scope)
    for seed in (17,52,1001):
        _,_,_,private=make_search_task(family+'-2',seed)
        matches=[]
        for data,expected in private:
            try:matches.append(same_json(scope['solve'](copy.deepcopy(data)),expected))
            except Exception:matches.append(False)
        assert not all(matches),name


def test_visible_tests_reject_floats_and_save_concise_counterexamples(tmp_path):
    _,files,_,_=make_search_task('reconcile-1',55)
    for name,content in files.items():(tmp_path/name).write_text(content)
    source=SOLUTIONS['reconcile']+'''\n_original=solve
def solve(data):
    result=_original(data)
    result['total_cents']=float(result['total_cents'])
    return result
'''
    (tmp_path/'solution.py').write_text(source)
    result=subprocess.run([sys.executable,'tests.py'],cwd=tmp_path,
                          capture_output=True,text=True,timeout=5)
    assert result.returncode!=0
    assert (tmp_path/'failure-0.json').exists()
    assert 'failure-0.json' in result.stderr and len(result.stderr)<3000
