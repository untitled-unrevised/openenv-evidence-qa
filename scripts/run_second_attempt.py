"""One bounded, authorized second Arena attempt and read-only completion monitor.

No credentials in arguments or artifacts. Default is a read-only preflight.
Posting requires --execute plus a frozen request hash and an eligible quota.
"""
import argparse
import fcntl
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from huggingface_hub import get_token

BASE='https://openenvarena-arena.hf.space'


def write_json(path,data):
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(data,indent=2)+'\n')
    temporary.replace(path)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--request',required=True)
    p.add_argument('--sha256',required=True)
    p.add_argument('--not-before',type=float,required=True)
    p.add_argument('--output',required=True)
    p.add_argument('--execute',action='store_true')
    args=p.parse_args()
    raw=Path(args.request).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=args.sha256:raise SystemExit('Frozen request hash mismatch')
    request=json.loads(raw);sid=request['submission_id']
    if sid!='evidence-search-v2-20261014':raise SystemExit('Unexpected second-attempt id')
    if '@sha256:' not in request['image']:raise SystemExit('Image must be pinned by digest')
    if request.get('dataset')!='hieudhgdfgdfg/evidence-search-v2':raise SystemExit('Unexpected dataset')
    output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
    with (output/'operator.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        token=get_token()
        if not token:raise SystemExit('No stored HF credential')
        session=requests.Session();session.headers['Authorization']='Bearer '+token
        def get(path):
            response=session.get(BASE+path,timeout=30,allow_redirects=False)
            response.raise_for_status();return response.json()
        def status(state,**extra):
            data={'state':state,'submission_id':sid,
                  'updated_at':datetime.now(timezone.utc).isoformat(),**extra}
            write_json(output/'operator-status.json',data)
            print(json.dumps(data),flush=True)
        listing=get('/api/openenv/submissions')
        existing=next((s for s in listing.get('submissions',[]) if s.get('submission_id')==sid),None)
        eligibility=max([args.not_before]+[float(s.get('slot',{}).get('window_ends_at') or 0)
                                           for s in listing.get('submissions',[])
                                           if s.get('slot',{}).get('state') in ('held','used')])
        if not args.execute:
            status('read_only_preflight',existing=existing is not None,
                   earliest_submission_utc=datetime.fromtimestamp(eligibility,timezone.utc).isoformat(),
                   eligible_now=time.time()>=eligibility,request_sha256=args.sha256)
            return
        deadline=time.monotonic()+24*3600
        # Resuming an accepted run must never create another submission.
        if existing is None:
            if (output/'post-attempted.json').exists():
                status('ambiguous_previous_post_requires_inspection')
                return
            while time.time()<eligibility:
                if time.monotonic()>=deadline:
                    status('quota_wait_deadline');return
                status('waiting_for_quota',eligible_at=eligibility)
                time.sleep(min(60,max(0.1,eligibility-time.time())))
            # Refresh quota directly before posting, after any scheduled wait.
            listing=get('/api/openenv/submissions')
            existing=next((s for s in listing.get('submissions',[]) if s.get('submission_id')==sid),None)
            for row in listing.get('submissions',[]):
                end=float(row.get('slot',{}).get('window_ends_at') or 0)
                if row.get('slot',{}).get('state') in ('held','used') and end>time.time():
                    status('quota_changed_no_post',eligible_at=end);return
            if existing is None:
                write_json(output/'post-attempted.json',{'submission_id':sid,'at':time.time(),
                                                        'request_sha256':args.sha256})
                try:
                    response=session.post(BASE+'/api/openenv/submissions',json=request,
                                          timeout=60,allow_redirects=False)
                    try:body=response.json()
                    except ValueError:body={'http_status':response.status_code}
                    write_json(output/'submission-response.json',body)
                    if not response.ok:
                        status('post_refused_no_retry',http_status=response.status_code);return
                except requests.RequestException:
                    # A timeout may have followed acceptance. Query by id below;
                    # never repeat this POST or create an alternate id.
                    status('post_response_unconfirmed_read_only_monitor')
        last_state=None;unavailable=0
        while time.monotonic()<deadline:
            try:
                current=get('/api/openenv/submissions/'+sid)
                write_json(output/'submission-latest.json',current)
                unavailable=0
            except requests.RequestException:
                unavailable+=1
                if unavailable>=30:
                    status('monitor_unavailable_no_repost');return
                time.sleep(60);continue
            if current.get('submission_id')!=sid:
                status('unexpected_response_no_repost');return
            if current.get('simulated'):
                status('simulation_detected_no_score_claim');return
            state=current.get('state');run=current.get('run') or {};evaluation=current.get('evaluation') or {}
            key=(state,run.get('state'),evaluation.get('state'),run.get('run_id'))
            if key!=last_state:
                status('monitoring',submission_state=state,run_state=run.get('state'),
                       evaluation_state=evaluation.get('state'),run_id=run.get('run_id'),
                       dashboard=run.get('dashboard'))
                last_state=key
            if evaluation.get('state')=='done':
                solved,total=evaluation.get('solved'),evaluation.get('total')
                if not isinstance(solved,int) or total!=40:
                    status('unexpected_evaluation_format');return
                report=(f'# Second Arena run result\n\nSubmission: {sid}\n\n'
                        f'Run: {run.get("run_id")}\n\n'
                        f'Actual evaluation: **{solved}/{total} ({100*solved/total:.1f}%)**. '
                        f'V1 scored 3/40; the published untrained reference scored 4/40. '
                        f'This run differs by {solved-3:+d} solves from v1 and '
                        f'{solved-4:+d} from that reference. One evaluation does not '
                        'establish a reliable training effect.\n\n'
                        f'Dashboard: {run.get("dashboard")}\n\n'
                        'Per-domain results:\n\n'+
                        ''.join(f'- {d}: {v.get("solved")}/{v.get("total")}\n'
                                for d,v in evaluation.get('scores',{}).items()))
                try:
                    board=get('/api/leaderboard');write_json(output/'leaderboard-final.json',board)
                    entry=next((e for e in board.get('entries',[]) if e.get('user')=='hieudhgdfgdfg'),None)
                    if entry:write_json(output/'account-final.json',entry)
                except requests.RequestException:pass
                (output/'result.md').write_text(report)
                write_json(output/'result.json',{'submission_id':sid,'run':run,'evaluation':evaluation})
                status('completed',solved=solved,total=total,result_file=str(output/'result.md'))
                return
            if state in ('rejected','failed','cancelled','canceled'):
                status('ended_without_evaluation',submission_state=state,
                       error_code=current.get('error_code'));return
            time.sleep(60)
        status('monitor_deadline_no_result_claim')


if __name__=='__main__':main()
