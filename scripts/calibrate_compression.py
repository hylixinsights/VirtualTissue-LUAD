"""B26 structural calibration with an independent B27 spatial holdout.

Nuclear/cell area ratios constrain a 2D lower-area proxy. They do not identify
compressibility, 3D cell volumes or any biological kinetic rate.
"""
import argparse,copy,sys,time
from pathlib import Path
from collections import defaultdict
import h5py,numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from luad_tissue.io import read_json,write_json,file_hash
from luad_tissue.v2.autonomous import AutonomousSimulation
from luad_tissue.v2.episode import engine_fingerprint


def column(obs,name):
    x=obs[name]
    if isinstance(x,h5py.Group):return x['categories'][()][x['codes'][()]]
    return x[()]


def derive(data,atlas,factor,mobility):
    assert .1<=factor<=1.5 and .01<=mobility<=2
    with h5py.File(data) as f:
        obs=f['obs'];ids=column(obs,'cell_id');nuclear=column(obs,'nucleus_area');areas=column(obs,'cell_area')
    lookup={int(cid):(float(n),float(a)) for cid,n,a in zip(ids,nuclear,areas)}
    groups=defaultdict(list);excluded=0
    for c in atlas['cells']:
        if c['role']!='roi' or c['cell_id'] not in lookup:continue
        nucleus,area=lookup[c['cell_id']]
        if not (np.isfinite([nucleus,area]).all() and 0<nucleus<=area and area>0):excluded+=1;continue
        groups[c['identity']['candidates'][0]['label']].append(nucleus/area)
    pooled=[v for values in groups.values() for v in values]
    fallback=float(np.clip(np.quantile(pooled,.1)*factor,.1,.8))
    stats={label:dict(n=len(values),q10=float(np.quantile(values,.1)),median=float(np.median(values)),q90=float(np.quantile(values,.9))) for label,values in sorted(groups.items())}
    fractions={label:float(np.clip(s['q10']*factor,.1,.8)) if s['n']>=5 else fallback for label,s in stats.items()}
    contract=read_json(ROOT/'contracts/runtime-v2.json')
    contract.update(version='luad-runtime-0.2.1',status='Structural compression calibration; kinetic rates remain declared assumptions.')
    contract['mechanics']['mobility_per_min']=mobility
    contract['geometry']['recover_initial_hidden']=True
    contract['mechanics']['rescue'].update(kappa_factor_per_substep=1.,kappa_max_times_initial=1.,note='Disabled for the constrained mechanics profile; weights cannot inflate to rescue compressed cells.')
    contract['mechanics']['compression_constraint']=dict(area_floor_fraction_by_label=fractions,fallback_fraction=fallback,max_backtracks=4,max_freeze_passes=4,
            method='B26 ROI nucleus/cell area q10 by primary type, multiplied by sensitivity factor, clipped 0.1–0.8. Local motion backtracking; growth/division/insertion must preserve all lower areas.',factor=factor)
    contract['biology']['initialize_cycle_phase_from_annotation']=False
    contract['calibration']=dict(training_patch='LUAD3_B26',holdout_patch='LUAD3_B27',source_sha256=file_hash(data),
        observation_columns=['nucleus_area','cell_area','cell_id'],excluded_invalid_rows=excluded,ratio_statistics=stats,
        scope='Empirical 2D structural proxy; neither physical stiffness nor kinetic rates are identified by a single static section.',
        kinetics='Unchanged proposed clocks. Unobserved initial cycle phase no longer creates instantaneous area jumps.',
        primary_sources=['https://www.jci.org/articles/view/45817','https://doi.org/10.1016/j.bpj.2014.08.031'])
    return contract


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--factor',type=float,default=1.);p.add_argument('--mobility',type=float,default=.2)
    p.add_argument('--region',type=int,choices=[26,27],default=26);p.add_argument('--hours',type=int,default=6)
    p.add_argument('--scenario',default='S1');p.add_argument('--seed',type=int,default=21)
    p.add_argument('--tag',required=True);p.add_argument('--contract',type=Path)
    p.add_argument('--data',type=Path,default=ROOT.parent/'LUAD3_TLS_GO20_UCell.h5ad')
    args=p.parse_args()
    base=read_json(ROOT/'outputs/atlas_B26.json.gz')
    contract=read_json(args.contract) if args.contract else derive(args.data,base,args.factor,args.mobility)
    contract['run']['horizon_min']=args.hours*60
    folder=ROOT/'outputs/calibration-20260929';folder.mkdir(exist_ok=True)
    write_json(folder/(args.tag+'.contract.json'),contract)
    atlas=base if args.region==26 else read_json(ROOT/'outputs/atlas_B27.json.gz')
    sim=AutonomousSimulation(atlas,contract,args.scenario,args.seed)
    start=time.monotonic();last=-1
    while not sim.stop_reason:
        sim.step()
        if sim.time//360!=last:
            last=sim.time//360
            print(args.tag,sim.time/60,'h; hidden',sim.metrics[-1]['hidden'],'min/floor',sim.metrics[-1].get('area_min_over_floor'),flush=True)
    t=sim.tissue
    groups={}
    for label in set(t.labels):
        rows=[g for g in range(len(t.ids)) if t.labels[g]==label and t.origins[g]=='roi' and t.present[g]]
        if rows:groups[label]=dict(n=len(rows),median_net_um=float(np.median(np.linalg.norm(t.xy[rows]-t.xy0[rows],axis=1))))
    report=dict(tag=args.tag,seconds=time.monotonic()-start,engine_fingerprint=sim.engine_fingerprint,summary=sim.summary(),
                peak_hidden=max(m['hidden'] for m in sim.metrics),min_area_over_floor=min(m.get('area_min_over_floor',1) for m in sim.metrics),
                displacement_by_label=groups,initial_fidelity=sim.fidelity,overlap=t.overlap_audit())
    write_json(folder/(args.tag+'.report.json'),report)
    write_json(folder/(args.tag+'.luad2.json.gz'),sim.episode())
    print(args.tag,'COMPLETE',report['seconds'],'seconds; peak hidden',report['peak_hidden'],'final tumor',report['summary']['final']['tumour_cells'],flush=True)


if __name__=='__main__':main()
