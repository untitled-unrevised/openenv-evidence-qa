import copy
import json

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
