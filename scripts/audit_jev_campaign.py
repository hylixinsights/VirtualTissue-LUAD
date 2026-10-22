"""Audit recorded Jev decisions against their durable paid-response receipts."""
import argparse,json,sys
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from luad_tissue.io import fingerprint,read_json,write_json
from luad_tissue.v2.episode import validate_episode
from luad_tissue.v2.provider_jev import normalize_answer


def audit(campaign,episode_path,atlas_path):
    campaign,episode_path,atlas_path=map(Path,(campaign,episode_path,atlas_path))
    episode,atlas=read_json(episode_path),read_json(atlas_path);validate_episode(episode,atlas)
    if episode['provider']!='jev_batched_v2':raise ValueError('Expected actual recorded Jev decisions')
    ledger=[json.loads(x) for x in (campaign/'usage.jsonl').read_text().splitlines()]
    authorization=read_json(campaign/'authorization.json')
    if len(ledger)>authorization['max_requests']:raise ValueError('Campaign ceiling exceeded')
    intents={};results={};usage=Counter();statuses=Counter();unknown=0;latencies=[]
    journal=episode_path.with_name(episode_path.name.replace('-jev.luad2.json.gz','-jev.audit.jsonl'))
    with journal.open(encoding='utf8') as stream:
        for line in stream:
            row=json.loads(line)
            if row['phase']=='intent':
                if fingerprint(row['request'])!=row['hash']:raise ValueError('Request hash mismatch')
                if row['hash'] in intents:raise ValueError('A paid request was duplicated')
                intents[row['hash']]=row
            elif row['phase']=='result':
                if row['hash'] not in intents or row['hash'] in results:raise ValueError('Unmatched or duplicate result')
                results[row['hash']]=row;statuses[row['status']]+=1
                if isinstance(row.get('usage'),dict):
                    for k,v in row['usage'].items():
                        if isinstance(v,(int,float)):usage[k]+=v
                else:unknown+=1
                if isinstance(row.get('latency_s'),(int,float)):latencies.append(row['latency_s'])
    if len(intents)!=episode['paid_calls']:raise ValueError('Episode and journal call counts differ')
    current=[r for r in ledger if not r.get('carried_from')]
    if Counter(x['request_hash'] for x in current)!=Counter(intents.keys()):raise ValueError('Global budget and paid journal disagree')
    if len(results)!=len(intents):raise ValueError('Unresolved paid request; preserve for review')
    receipt={};models=set();repairs=Counter()
    for digest,row in results.items():
        if row['status']!='received':raise ValueError('Failed request remains in the selected trajectory')
        response=row['response'];models.add(response.get('model'))
        questions=intents[digest]['request']['questions'];answers=response.get('answers',{})
        for name,question in questions.items():
            cid=int(name[1:]);key=(cid,fingerprint(question['instructions']['local_observation']))
            normalized=normalize_answer(answers.get(name),question['criteria'],episode['contract']['provider'])
            repairs.update(normalized['repairs'])
            receipt.setdefault(key,[]).append((normalized,set(question['criteria'])))
    if len(models)!=1 or None in models:raise ValueError('Missing or changing returned model')
    observed=Counter();choice_counts=Counter();bytype=Counter()
    for d in episode['decisions']:
        key=(d['cell_id'],fingerprint(d['observation']))
        choices=receipt.get(key,[])
        matching=[x for x in choices if x[0]==d['answer'] and x[1]==set(d['options'])]
        if not matching:raise ValueError('Applied decision has no exact validated provider receipt')
        choices.remove(matching[0]);observed[key]+=1
        bytype[d['observation']['primary_label']]+=1;choice_counts[d['answer']['choice'].split(':')[0]]+=1
    if episode['summary']['invalid_answers']:raise ValueError('Selected trajectory contains invalid individual answers')
    if sum(len(v) for v in receipt.values()):raise ValueError('Paid answers missing from recorded decisions')
    if {'B_cell','Plasma_cell','occluded'}.intersection(bytype):raise ValueError('Quiet/context cell queried')
    days=Counter((d['cell_id'],d['time_min']//1440) for d in episode['decisions'])
    if max(days.values(),default=0)>episode['contract']['scheduler']['max_per_cell_day']:raise ValueError('Daily cell cap exceeded')
    from statistics import median
    report=dict(format='luad-jev-campaign-audit-v1',verified=True,
        cumulative_requests=len(ledger),carried_requests=len(ledger)-len(current),run_requests=len(intents),
        authorized_ceiling=authorization['max_requests'],remaining=authorization['max_requests']-len(ledger),
        modeled_hours=episode['summary']['time_min']/60,stop_reason=episode['summary']['stop_reason'],
        questions=len(episode['decisions']),returned_model=next(iter(models)),invalid=0,
        repairs=dict(repairs),usage=dict(usage),unknown_usage_requests=unknown,
        median_request_latency_seconds=median(latencies) if latencies else None,
        choices=dict(choice_counts),decisions_by_type=dict(bytype),
        episode_fingerprint=episode['fingerprint'],engine_fingerprint=episode.get('engine_fingerprint'),
        scope='Every recorded decision matched the normalized reply and exact local observation/menu. No biological validity or dollar cost is inferred from response validity.')
    write_json(campaign/'verified-campaign.json',report)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--campaign',type=Path,required=True);p.add_argument('--episode',type=Path,required=True)
    p.add_argument('--atlas',type=Path,default=ROOT/'outputs/atlas_B26.json.gz')
    a=p.parse_args();print(json.dumps(audit(a.campaign,a.episode,a.atlas),indent=2))
