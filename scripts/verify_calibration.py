"""Audit completed calibrated experiments, including mechanical stagnation."""
import argparse,sys
from pathlib import Path
from collections import Counter
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from luad_tissue.io import read_json,write_json
from luad_tissue.v2.episode import validate_episode,engine_fingerprint


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory',type=Path,default=ROOT/'outputs/calibrated-final')
    args=p.parse_args();rows=[];atlases={}
    for path in sorted(args.directory.glob('*.luad2.json.gz')):
        e=read_json(path)
        if e['summary']['stop_reason']!='horizon_reached':continue
        region=27 if e['patch_id'].endswith('B27') else 26
        if region not in atlases:atlases[region]=read_json(ROOT/f'outputs/atlas_B{region}.json.gz')
        validate_episode(e,atlases[region])
        assert e['engine_fingerprint']==engine_fingerprint(),'Recording uses a superseded numerical solver'
        m=e['metrics'];final=m[-1]
        assert max(x['hidden'] for x in m)==0
        assert min(x['area_min_over_floor'] for x in m)>=1-1e-7
        assert max(x['field_balance_max'] for x in m)<1e-6
        assert max(x['field_residual_max'] for x in m)<1e-7
        counts=Counter((d['cell_id'],d['time_min']//1440) for d in e['decisions'])
        assert max(counts.values(),default=0)<=e['contract']['scheduler']['max_per_cell_day']
        assert all(d['observation']['primary_label'] not in ('B_cell','Plasma_cell','occluded') for d in e['decisions'])
        acc=e['summary']['accounting']
        assert sum(acc['acting'].values())==acc['expected_acting_total']
        assert acc['context_total']==acc['expected_context_total']
        if e['scenario'] in ('static','recognition_off'):
            assert not e['summary']['events'].get('cytotoxic_pulse',0)
            assert not e['summary']['events'].get('apoptosis_committed',0)
        if e['scenario']=='static':
            assert not e['events'] and not e['decisions']
            assert e['frames'][0]['x']==e['frames'][-1]['x'] and e['frames'][0]['y']==e['frames'][-1]['y']
        report=read_json(path.with_name(path.name.replace('.luad2.json.gz','.report.json')))
        assert report['episode_fingerprint']==e['fingerprint']
        assert abs(report['overlap']['relative_overlap'])<1e-8
        start,end=e['frames'][0],e['frames'][-1]
        lookup={cid:j for j,cid in enumerate(end['ids'])};labels={c['cell_id']:c for c in atlases[region]['cells']}
        shifts={}
        for j,cid in enumerate(start['ids']):
            if cid not in lookup or labels[cid]['role']!='roi':continue
            k=lookup[cid];label=labels[cid]['identity']['candidates'][0]['label']
            shifts.setdefault(label,[]).append(float(np.hypot(end['x'][k]-start['x'][j],end['y'][k]-start['y'][j])))
        rows.append(dict(file=path.name,region=region,scenario=e['scenario'],seed=e['seed'],hours=e['summary']['time_min']/60,
            provider=e['provider'],paid_calls=e['paid_calls'],tumor=final['tumour_cells'],death_commitments=final['kills'],
            recruited=final['recruited'],hidden_peak=max(x['hidden'] for x in m),minimum_area_over_floor=min(x['area_min_over_floor'] for x in m),
            zero_motion_ticks=sum(x['max_substep_um']<1e-5 for x in m),ticks=len(m),
            global_rollbacks=final['compression_global_rollbacks'],local_freezes=final['compression_local_freezes'],
            growth_steps_blocked=final['growth_steps_blocked'],insertion_trials_blocked=final['insertion_trials_blocked'],
            median_displacement_um={k:float(np.median(v)) for k,v in shifts.items()},
            decisions=e['summary']['decisions'],invalid=e['summary']['invalid_answers'],estimated_requests=e['summary']['estimated_requests'],
            fingerprint=e['fingerprint'],engine_fingerprint=e['engine_fingerprint']))
        print(path.name,'verified; hidden',rows[-1]['hidden_peak'],'zero-motion ticks',rows[-1]['zero_motion_ticks'],'/',len(m),flush=True)
    if not rows:raise SystemExit('No completed matching calibrated recording found')
    write_json(args.directory/'calibration-verification.json',dict(format='luad-calibration-verification',runs=rows))


if __name__=='__main__':main()
