"""Independent scripted solutions used only in local checks, outside images."""
SOLUTIONS = {
    'reconcile': '''def solve(data):
    balances={r['id']:r['cents'] for r in data['invoices'] if r['status']=='posted'}
    for a in sorted(data['amendments'],key=lambda a:a['revision']):
        if a['invoice'] in balances: balances[a['invoice']]=a['cents']
    seen=set()
    for p in data['payments']:
        if p['id'] not in seen:
            if p['invoice'] in balances: balances[p['invoice']]-=p['cents']
            seen.add(p['id'])
    for c in data['credits']:
        if c['status']=='posted' and c['invoice'] in balances:balances[c['invoice']]-=c['cents']
    return {'balances':balances,'total_cents':sum(balances.values())}
''',
    'dialogue': r'''import re
def solve(data):
    nodes=[];edges=[];current=None
    for raw in data['text'].splitlines():
        s=raw.strip()
        if not s:continue
        if re.fullmatch(r'\[[^\]]+\]',s):
            current={'id':s[1:-1],'type':'line','speaker':'','text':''};nodes.append(current)
        else:
            body,target=s.rsplit('->',1);body=body.strip();target=target.strip()
            m=re.match(r'^\d+\.\s*(.*)$',body)
            if m:current['type']='choice';text=m.group(1)
            else:
                speaker,text=body.split(':',1);current['speaker']=speaker.strip();current['text']=text.strip();text=''
            edges.append({'from':current['id'],'to':target,'text':text})
    return {'nodes':nodes,'edges':edges}
''',
    'dependencies': '''import heapq
def solve(data):
    edges=set(map(tuple,data['edges']));out={n:[] for n in data['nodes']};degree={n:0 for n in out}
    for a,b in edges:out[a].append(b);degree[b]+=1
    ready=[n for n in out if degree[n]==0];heapq.heapify(ready);order=[]
    while ready:
        n=heapq.heappop(ready);order.append(n)
        for b in out[n]:
            degree[b]-=1
            if degree[b]==0:heapq.heappush(ready,b)
    return {'order':order if len(order)==len(out) else None}
''',
    'intervals': '''import itertools
def solve(data):
    best_value=0;best_ids=[];jobs=data['jobs']
    for size in range(len(jobs)+1):
        for selected in itertools.combinations(jobs,size):
            ordered=sorted(selected,key=lambda x:x['start'])
            if any(a['end']>b['start'] for a,b in zip(ordered,ordered[1:])):continue
            val=sum(j['value'] for j in selected);ids=sorted(j['id'] for j in selected)
            if val>best_value or (val==best_value and ids<best_ids):best_value,best_ids=val,ids
    return {'ids':best_ids,'value':best_value}
''',
}
