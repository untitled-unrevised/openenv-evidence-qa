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
    if family == 'reconcile':
        n=2+level;ids=[f'I{rng.randrange(1000,9999)}-{i}' for i in range(n)]
        invoices=[{'id':s,'cents':rng.randrange(1000,20000),'status':'posted' if i<n-1 else 'void'} for i,s in enumerate(ids)]
        payments=[{'id':f'P{i}','invoice':s,'cents':rng.randrange(1,800)} for i,s in enumerate(ids)]
        payments.append(dict(payments[0]));rng.shuffle(payments)
        amendments=[{'invoice':ids[0],'revision':r,'cents':rng.randrange(1000,20000)} for r in (3,1,2)]
        credits=[{'invoice':ids[0],'cents':100,'status':'draft'},{'invoice':ids[1],'cents':50,'status':'posted'}]
        rng.shuffle(invoices)
        return {'invoices':invoices,'amendments':amendments,'payments':payments,'credits':credits}
    if family == 'dialogue':
        token=str(rng.randrange(100,999));start='Entry'+token;branch='Select'+token
        lines=[f'[{start}]',f'Narrator: Note: ticket {index} -> {branch}','',f'[{branch}]']
        for i in range(1,level+3):lines.append(f'{i}. [Wait] route {i}: ticket {token} -> Path{token}_{i}')
        for i in range(1,level+3):lines.extend(['',f'[Path{token}_{i}]',f'Guide: Arrival {i} -> End'])
        sep='\r\n' if index%2 else '\n'
        return {'text':sep.join(lines)+'\n'}
    if family == 'dependencies':
        nodes=[f'{c}{rng.randrange(10,99)}' for c in 'ABCDEFG'[:level+3]]
        order=nodes[:];rng.shuffle(order)
        edges=[[order[i],order[j]] for i in range(len(nodes)) for j in range(i+1,len(nodes)) if rng.random()<0.35]
        if index%4==0:edges.extend([[nodes[0],nodes[1]],[nodes[1],nodes[0]]])
        if edges:edges.append(edges[0][:])
        rng.shuffle(nodes);rng.shuffle(edges)
        return {'nodes':nodes,'edges':edges}
    jobs=[]
    for i in range(3+2*level):
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
        for case in json.load(open('examples.json')):
            with self.subTest(input=case['input']):
                data=copy.deepcopy(case['input']); before=copy.deepcopy(data)
                self.assertEqual(solve(data),case['expected'])
                self.assertEqual(data,before,'Input must not be mutated')
if __name__=='__main__': unittest.main()
'''
    files={'solution.py':STARTERS[family], 'contract.txt':CONTRACTS[family],
           'examples.json':json.dumps(examples,ensure_ascii=False), 'tests.py':tests}
    instruction=('Repair solution.py so solve(data) obeys contract.txt on new inputs. '
                 'Read the contract and run python tests.py to reproduce failures. '
                 'Use the counterexamples to revise the implementation and rerun tests. '
                 'Public tests are examples, not the complete specification. '
                 'You may add tests and scratch files. Do not hardcode examples. '
                 'solve must return JSON-serializable values without mutating its input. '
                 'check runs the original public examples against a fresh copy of your solution. '
                 'submit or finish ends the episode and grades independent private cases. '
                 'Tools: list/read/write/shell/check/submit/finish. Files persist; each shell '
                 'command has 10 seconds. Python standard library is available. '
                 'Keep output short. Budget:64 actions. No report.json is needed.\n'+CONTRACTS[family])
    return instruction,files,examples,[(d,reference(family,d)) for d in private]
