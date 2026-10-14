"""Posting boundaries: all HTTP and credentials are faked; no live mutations."""
import hashlib
import importlib.util
import json
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest
import requests

spec=importlib.util.spec_from_file_location('second_attempt',Path(__file__).parents[1]/'scripts/run_second_attempt.py')
operator=importlib.util.module_from_spec(spec);spec.loader.exec_module(operator)
SID='evidence-search-v2-20261014'


class Response:
    def __init__(self,data,status=200):self.data=data;self.status_code=status;self.ok=status<400
    def json(self):return self.data
    def raise_for_status(self):
        if not self.ok:raise requests.HTTPError(str(self.status_code))


class Session:
    def __init__(self,listings,post='ok'):
        self.headers={};self.listings=iter(listings);self.posts=[];self.post_behavior=post
    def get(self,url,**kwargs):
        if url.endswith('/submissions'):return Response(next(self.listings))
        if url.endswith('/'+SID):return Response({'submission_id':SID,'state':'done','simulated':False,
             'run':{'run_id':'test-run','state':'completed'},
             'evaluation':{'state':'done','solved':5,'total':40,'scores':{}}})
        if url.endswith('/leaderboard'):return Response({'entries':[]})
        raise AssertionError(url)
    def post(self,url,**kwargs):
        self.posts.append(kwargs['json'])
        if self.post_behavior=='timeout':raise requests.Timeout()
        if self.post_behavior=='refused':return Response({'error':'quota'},429)
        return Response({'submission_id':SID,'state':'accepted'})


def run(tmp_path,monkeypatch,session,execute=False,marker=False):
    request=tmp_path/'request.json';output=tmp_path/'output'
    raw=json.dumps({'submission_id':SID,'image':'ghcr.io/untitled-unrevised/evidence-qa@sha256:'+'a'*64,
                    'dataset':'hieudhgdfgdfg/evidence-search-v2'}).encode();request.write_bytes(raw)
    args=['operator','--request',str(request),'--sha256',hashlib.sha256(raw).hexdigest(),
          '--not-before','0','--dataset-revision','verified-dataset','--output',str(output)]
    if execute:args.append('--execute')
    if marker:output.mkdir();(output/'post-attempted.json').write_text('{}')
    monkeypatch.setattr(sys,'argv',args)
    monkeypatch.setattr(operator,'get_token',lambda:'fake-not-a-credential')
    monkeypatch.setattr(operator,'HfApi',lambda **kwargs:SimpleNamespace(dataset_info=lambda repo:SimpleNamespace(sha='verified-dataset')))
    monkeypatch.setattr(operator.requests,'Session',lambda:session)
    operator.main()
    return json.loads((output/'operator-status.json').read_text())


def test_default_preflight_never_posts(tmp_path,monkeypatch):
    session=Session([{'submissions':[]}])
    assert run(tmp_path,monkeypatch,session)['state']=='read_only_preflight'
    assert session.posts==[]


def test_resume_existing_run_never_posts(tmp_path,monkeypatch):
    session=Session([{'submissions':[{'submission_id':SID}]}])
    assert run(tmp_path,monkeypatch,session,execute=True)['state']=='completed'
    assert session.posts==[]


def test_ambiguous_previous_post_is_not_repeated(tmp_path,monkeypatch):
    session=Session([{'submissions':[]}])
    assert run(tmp_path,monkeypatch,session,execute=True,marker=True)['state']=='ambiguous_previous_post_requires_inspection'
    assert session.posts==[]


@pytest.mark.parametrize('behavior',['ok','timeout'])
def test_post_once_then_monitor_even_after_timeout(tmp_path,monkeypatch,behavior):
    session=Session([{'submissions':[]},{'submissions':[]}],post=behavior)
    assert run(tmp_path,monkeypatch,session,execute=True)['state']=='completed'
    assert len(session.posts)==1


def test_refusal_does_not_retry(tmp_path,monkeypatch):
    session=Session([{'submissions':[]},{'submissions':[]}],post='refused')
    assert run(tmp_path,monkeypatch,session,execute=True)['state']=='post_refused_no_retry'
    assert len(session.posts)==1


def test_new_quota_holder_prevents_post(tmp_path,monkeypatch):
    other={'submission_id':'someone-else','slot':{'state':'used','window_ends_at':9999999999}}
    session=Session([{'submissions':[]},{'submissions':[other]}])
    assert run(tmp_path,monkeypatch,session,execute=True)['state']=='quota_changed_no_post'
    assert session.posts==[]


def test_run_accepted_during_wait_is_monitored_without_reposting(tmp_path,monkeypatch):
    own={'submission_id':SID,'slot':{'state':'used','window_ends_at':9999999999}}
    session=Session([{'submissions':[]},{'submissions':[own]}])
    assert run(tmp_path,monkeypatch,session,execute=True)['state']=='completed'
    assert session.posts==[]
