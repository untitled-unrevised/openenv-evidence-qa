"""Original synthetic code-repair curricula; no public benchmark instances.

Reference calculations remain in the root-only server package. The agent sees
the contract, a buggy candidate, and public examples, but no private cases.
"""
import json
import random
import secrets

SEARCH_TASKS = {f"{family}-{level}": (family, level)
                for family in ("reconcile", "dialogue", "dependencies", "intervals")
                for level in range(1, 4)}

CONTRACTS = {
    "reconcile": '''Implement solve(data). data has invoices [{id,cents,status}],
amendments [{invoice,revision,cents}], payments [{id,invoice,cents}], and credits
[{invoice,cents,status}]. Include only posted invoices. Highest amendment revision
replaces gross cents regardless of file order. Subtract payments once per payment
id and posted credits only. Ignore entries for excluded invoices. Return
{"balances": {invoice_id: integer_cents}, "total_cents": integer_cents}.''',
    "dialogue": '''Implement solve(data), where data={"text": script_string}.
A script has [NodeID] headers. A line node contains Speaker: Text -> Target.
A choice node contains numbered lines N. Choice text -> Target; preserve tags
such as [Wait] in choice text, but remove the number. Strip surrounding whitespace.
Return {"nodes":[{"id":str,"type":"line|choice","speaker":str,"text":str}],
"edges":[{"from":str,"to":str,"text":str}]}. Keep source order. Choice nodes
have empty speaker and text. Line-edge text is empty. Terminal End may be a target
but is not an implicit node. Every header creates exactly one node. Blank lines
are ignored. Each line node has one dialogue line, choices have one or more lines.
Use the last -> to separate an edge target; text may contain colons.''',
    "dependencies": '''Implement solve(data). data={"nodes":[unique strings],
"edges":[[prerequisite,dependent],...]}. Return {"order": list_of_nodes} in
topological order. Include isolated nodes. Repeated edges count once. At each
step choose the lexicographically smallest currently available node (Python string
order). If any cycle exists, return {"order": null}, even if some nodes can be
processed. Edges refer to listed nodes. Do not mutate the input.''',
    "intervals": '''Implement solve(data). data={"jobs":[{"id":str,"start":int,
"end":int,"value":int},...]}. Choose a subset of non-overlapping half-open
intervals [start,end), maximizing total value. Touching endpoints are compatible.
Empty selection is allowed. Each job has start<end and a unique id. Return
{"ids": selected_ids_sorted_lexicographically, "value": integer_total}.
Break equal-value ties by the lexicographically smallest sorted id list using
Python list comparison. There are at most 12 jobs. Do not mutate input.''',
}

STARTERS = {
    "reconcile": '''def solve(data):
    balances = {r['id']: r['cents'] for r in data['invoices'] if r['status'] == 'posted'}
    for a in data['amendments']:
        if a['invoice'] in balances: balances[a['invoice']] = a['cents']
    for p in data['payments']:
        if p['invoice'] in balances: balances[p['invoice']] -= p['cents']
    for c in data['credits']:
        if c['invoice'] in balances: balances[c['invoice']] -= c['cents']
    return {'balances': balances, 'total_cents': sum(balances.values())}
''',
    "dialogue": r'''import re
def solve(data):
    nodes, edges, current = [], [], None
    for raw in data['text'].splitlines():
        line = raw.strip()
        if not line: continue
        if line.startswith('[') and line.endswith(']'):
            current = {'id':line[1:-1], 'type':'line', 'speaker':'', 'text':''}
            nodes.append(current)
        elif current:
            body, target = line.rsplit('->', 1)
            if re.match(r'^\d+\.', body):
                current['type'] = 'choice'
                edges = [e for e in edges if e['from'] != current['id']]
                edges.append({'from':current['id'], 'to':target.strip(), 'text':body.strip()})
            else:
                speaker, text = body.split(':', 1)
                current['speaker'], current['text'] = speaker.strip(), text.strip()
                edges.append({'from':current['id'], 'to':target.strip(), 'text':''})
    return {'nodes':nodes, 'edges':edges}
''',
    "dependencies": '''def solve(data):
    order = []
    for node in sorted(data['nodes']):
        if all(a in order for a,b in data['edges'] if b == node): order.append(node)
    return {'order': order}
''',
    "intervals": '''def solve(data):
    chosen, end, value = [], -10**9, 0
    for j in sorted(data['jobs'], key=lambda j:j['end']):
        if j['start'] >= end:
            chosen.append(j['id']); end = j['end']; value += j['value']
    return {'ids': sorted(chosen), 'value': value}
''',
}


def reference(family, data):
    if family == "reconcile":
        balances = {r['id']: r['cents'] for r in data['invoices'] if r['status']=='posted'}
        for key in balances:
            edits = [a for a in data['amendments'] if a['invoice']==key]
            if edits: balances[key] = max(edits, key=lambda a:a['revision'])['cents']
            unique = {p['id']:p for p in data['payments'] if p['invoice']==key}
            balances[key] -= sum(p['cents'] for p in unique.values())
            balances[key] -= sum(c['cents'] for c in data['credits']
                                 if c['invoice']==key and c['status']=='posted')
        return {'balances':balances, 'total_cents':sum(balances.values())}
    if family == "dialogue":
        import re
        blocks = re.split(r'(?m)^\s*\[([^\]\n]+)\]\s*$', data['text'])
        nodes,edges = [],[]
        for i in range(1,len(blocks),2):
            node_id = blocks[i].strip()
            lines = [line.strip() for line in blocks[i+1].splitlines() if line.strip()]
            choice = bool(re.match(r'^\d+\.',lines[0]))
            node = {'id':node_id, 'type':'choice' if choice else 'line','speaker':'','text':''}
            for line in lines:
                body, target = line.rsplit('->',1)
                if choice: text=re.sub(r'^\d+\.\s*','',body.strip())
                else:
                    speaker,text=body.split(':',1)
                    node['speaker'],node['text']=speaker.strip(),text.strip()
                    text=''
                edges.append({'from':node_id,'to':target.strip(),'text':text})
            nodes.append(node)
        return {'nodes':nodes,'edges':edges}
    if family == "dependencies":
        remaining=set(data['nodes']); edges=set(map(tuple,data['edges'])); order=[]
        while remaining:
            ready=sorted(n for n in remaining if not any(b==n and a in remaining for a,b in edges))
            if not ready:return {'order':None}
            order.append(ready[0]);remaining.remove(ready[0])
        return {'order':order}
    jobs=data['jobs'];best=(0,[])
    for mask in range(1<<len(jobs)):
        selected=[j for i,j in enumerate(jobs) if mask & (1<<i)]
        by_time=sorted(selected,key=lambda j:(j['start'],j['end']))
        if any(a['end']>b['start'] for a,b in zip(by_time,by_time[1:])):continue
        value=sum(j['value'] for j in selected);ids=sorted(j['id'] for j in selected)
        if value>best[0] or (value==best[0] and ids<best[1]):best=(value,ids)
    return {'ids':best[1],'value':best[0]}


def case(family, rng, level, index):
    scenario=index%8
    if family == 'reconcile':
        n=rng.randint(2,3+level)
        ids=[f'I{rng.randrange(1000,9999)}-{i}' for i in range(n)]
        invoices=[{'id':s,'cents':rng.randrange(1000,20000),
                   'status':'posted' if rng.random()<0.7 else 'void'} for s in ids]
        invoices[0]['status']='posted'
        if scenario==5:
            for row in invoices:row['status']='void'
        posted=[r['id'] for r in invoices if r['status']=='posted']
        payments=[{'id':f'P{i}','invoice':s,'cents':rng.randrange(1,800)}
                  for i,s in enumerate(rng.sample(ids,rng.randrange(n+1)))]
        if scenario in (2,4,6,7) and payments:
            payments.extend(dict(payments[0]) for _ in range(rng.randint(1,3)))
        if scenario in (4,7):
            payments.append({'id':'orphan-payment','invoice':'absent','cents':rng.randrange(100,999)})
        amendments=[]
        if scenario in (1,4,6,7):
            for identifier in rng.sample(ids,rng.randint(1,min(n,level+1))):
                revisions=rng.sample(range(1,12),rng.randint(2,4))
                edits=[{'invoice':identifier,'revision':rev,'cents':rng.randrange(1000,20000)}
                       for rev in revisions]
                rng.shuffle(edits)
                if scenario==1:edits.sort(key=lambda a:a['revision'])
                amendments.extend(edits)
        credits=[]
        if scenario in (3,4,6,7) and posted:
            credits.append({'invoice':rng.choice(posted),'cents':rng.randrange(51,2500),'status':'posted'})
            credits.append({'invoice':rng.choice(ids),'cents':rng.randrange(100,4000),'status':'draft'})
            if scenario in (4,7):
                credits.extend({'invoice':rng.choice(ids),'cents':rng.randrange(1,900),
                                'status':rng.choice(['posted','draft'])} for _ in range(level))
                credits.append({'invoice':'absent','cents':777,'status':'posted'})
        if scenario==6 and posted:
            payments.append({'id':'overpayment','invoice':posted[0],'cents':100000})
        rng.shuffle(invoices);rng.shuffle(payments);rng.shuffle(credits)
        return {'invoices':invoices,'amendments':amendments,'payments':payments,'credits':credits}
    if family == 'dialogue':
        n=1 if scenario==0 else rng.randint(level+2,level+6)
        identifiers=[f'{rng.choice(["Hall","Branch","Room","Desk"])}{rng.randrange(100,999)}_{i}'
                     for i in range(n)]
        lines=[]
        for i,identifier in enumerate(identifiers):
            lines.extend(['',f'[{identifier}]'])
            is_choice=n>1 and (i==1 or rng.random()<0.4)
            if is_choice:
                for choice_index in range(1,rng.randint(2,level+4)):
                    tag=rng.choice(['','[Go] ','[Wait] ','[Delay] '])
                    text=f'{tag}route {rng.randrange(10,99)}: ticket {index}'
                    if scenario in (1,4,7):text+=' -> the old label'
                    target=rng.choice(identifiers+['End'])
                    lines.append(f'{choice_index}. {text} -> {target}')
            else:
                text=f'Notice: status {rng.randrange(100,999)}'
                if scenario in (1,4,7):text+=' -> transition recorded'
                target=identifiers[i+1] if i+1<n else 'End'
                lines.append(f'{rng.choice(["Guide","Narrator","Analyst"])}: {text} -> {target}')
        if scenario in (2,4):
            lines=[('  '+line+'  ') if line else '' for line in lines]
        return {'text':rng.choice(['\n','\r\n']).join(lines)+'\n'}
    if family == 'dependencies':
        nodes=[f'{c}{rng.randrange(1,999)}' for c in 'ABCDEFGH'[:rng.randint(3,level+4)]]
        order=sorted(nodes,reverse=scenario==1)
        if scenario==7:rng.shuffle(order)
        if scenario in (0,1):edges=[list(p) for p in zip(order,order[1:])]
        else:
            edges=[[order[i],order[j]] for i in range(len(nodes)) for j in range(i+1,len(nodes))
                   if rng.random()<0.3]
        if scenario==2:
            edges=[[nodes[0],nodes[2]],[nodes[1],nodes[2]]]
        if scenario==3:edges=[]
        if scenario==4:edges.extend([[nodes[0],nodes[1]],[nodes[1],nodes[0]]])
        if scenario==5:edges.append([nodes[0],nodes[0]])
        if scenario==6:nodes,edges=[],[]
        if edges and scenario in (2,4,7):edges.extend([edges[0][:],edges[-1][:]])
        rng.shuffle(nodes);rng.shuffle(edges)
        return {'nodes':nodes,'edges':edges}
    token=str(rng.randrange(100,999));a,b,c,d=(prefix+token for prefix in 'ABCD')
    value=rng.randint(3,20);offset=rng.randint(-20,20)
    def job(identifier,start,end,amount):
        return {'id':identifier,'start':start+offset,'end':end+offset,'value':amount}
    if scenario==0:jobs=[job(a,0,2,value),job(b,2,4,value+1)]
    elif scenario==1:jobs=[job(a,0,1,1),job(b,1,4,1),job(c,0,4,value+3),job(d,4,6,2)]
    elif scenario==2:jobs=[job(b,0,4,value),job(a,0,4,value),job(c,4,6,2)]
    elif scenario==3:jobs=[job(a,0,2,-value),job(b,2,4,-1)]
    elif scenario==4:jobs=[job(a,0,5,1),job(b,1,4,value),job(c,2,6,2),job(d,4,7,3)]
    elif scenario==5:jobs=[]
    elif scenario==6:jobs=[job(a,-2,0,0),job(b,0,2,value),job(c,0,2,-1)]
    else:jobs=[]
    if scenario!=7:
        rng.shuffle(jobs)
        return {'jobs':jobs}
    for i in range(rng.randint(3,3+2*level)):
        start=rng.randrange(-3,15);end=start+rng.randrange(1,7)
        jobs.append({'id':f'J{i}-{rng.randrange(100,999)}','start':start,'end':end,'value':rng.randrange(-4,20)})
    rng.shuffle(jobs)
    return {'jobs':jobs}


def make_search_task(task_id, seed=None):
    family,level=SEARCH_TASKS[task_id]
    rng=random.Random(seed if seed is not None else secrets.randbits(64))
    public=[case(family,rng,level,i) for i in range(4)]
    private=[case(family,rng,level,i+4) for i in range(16)]
    examples=[{'input':d,'expected':reference(family,d)} for d in public]
    tests='''import copy,json,unittest
from solution import solve
class ContractChecks(unittest.TestCase):
    def test_examples(self):
        for index,case in enumerate(json.load(open('examples.json'))):
            with self.subTest(case=index):
                data=copy.deepcopy(case['input']); before=copy.deepcopy(data)
                try:
                    actual=solve(data)
                    equal=json.dumps(actual,sort_keys=True,allow_nan=False)==json.dumps(case['expected'],sort_keys=True,allow_nan=False)
                    valid=equal and data==before
                    details={'input':before,'expected':case['expected'],'actual':actual,'input_mutated':data!=before}
                except Exception as error:
                    valid=False
                    details={'input':before,'expected':case['expected'],'error':str(error)[:500]}
                if not valid:
                    with open('failure-'+str(index)+'.json','w') as out:
                        json.dump(details,out,ensure_ascii=False,default=repr)
                self.assertTrue(valid,'Example '+str(index)+' failed; inspect failure-'+str(index)+'.json')
if __name__=='__main__': unittest.main()
'''
    files={'solution.py':STARTERS[family], 'contract.txt':CONTRACTS[family],
           'examples.json':json.dumps(examples,ensure_ascii=False), 'tests.py':tests}
    instruction=('Repair solution.py so solve(data) obeys contract.txt on new inputs. '
                 'Read the contract and run python tests.py to reproduce failures. '
                 'Use the counterexamples to revise the implementation and rerun tests. '
                 'Failed examples save their input, expected and actual output in failure-N.json. '
                 'Public tests are examples, not the complete specification. '
                 'You may add tests and scratch files. Do not hardcode examples. '
                 'solve must return JSON-serializable values without mutating its input. '
                 'check runs the original public examples against a fresh copy of your solution. '
                 'submit or finish ends the episode and grades independent private cases. '
                 'Tools: list/read/write/shell/check/submit/finish. Files persist; each shell '
                 'command has 10 seconds. Python standard library is available. '
                 'Keep output short. Budget:64 actions. No report.json is needed.\n'+CONTRACTS[family])
    return instruction,files,examples,[(d,reference(family,d)) for d in private]
