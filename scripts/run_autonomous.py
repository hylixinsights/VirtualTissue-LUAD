"""Record autonomous LUAD experiments. Default: declared local policy, no API.

Live mode always performs a complete local dry-run estimate first, then
requires --live and an explicit total request cap. Resume reruns the kernel
deterministically using the durable journal, without repaying known requests.
"""
import argparse
import copy
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from luad_tissue.io import fingerprint,read_json,write_json
from luad_tissue.v2.autonomous import AutonomousSimulation
from luad_tissue.v2.episode import engine_fingerprint
from luad_tissue.v2.provider_jev import BatchedJevProvider


def record(atlas,contract,scenario,seed,path,provider=None,reviewed_concentration=False):
    sim = AutonomousSimulation(atlas,contract,scenario,seed,provider)
    start = time.perf_counter()
    last_save = -1
    try:
        while not sim.stop_reason:
            sim.step()
            if provider is not None and len(sim.decisions) >= 100:
                summary = sim.summary()
                if summary["decision_share_above_half"] and not reviewed_concentration:
                    sim.stop_reason = "pilot_review_decision_concentration"
                elif len(sim.failures)/len(sim.decisions) > .1:
                    sim.stop_reason = "pilot_review_systematic_invalid_answers"
            if provider is not None and any(a['status']=='batch_invalid_or_unknown' for a in provider.audit):
                sim.stop_reason = "provider_transport_or_model_review"
            if sim.time//360 != last_save or sim.stop_reason:
                write_json(path,sim.episode())
                last_save = sim.time//360
                print(f"{atlas['patch_id']} {scenario} seed {seed}: {sim.time/60:g} h; tumor {sim.metrics[-1]['tumour_cells'] if sim.metrics else 'initial'}; decisions {len(sim.decisions)}",flush=True)
    except KeyboardInterrupt:
        sim.stop_reason = "user_interrupted"
        write_json(path,sim.episode())
    elapsed = time.perf_counter()-start
    episode = sim.episode()
    write_json(path,episode)
    report = dict(format="luad-autonomous-report",patch_id=atlas["patch_id"],scenario=scenario,seed=seed,
                  contract_fingerprint=fingerprint(contract),atlas_fingerprint=atlas["fingerprint"],seconds=round(elapsed,2),
                  episode=path.name,episode_fingerprint=episode["fingerprint"],summary=sim.summary(),
                  initial_fidelity=sim.fidelity,overlap=sim.tissue.overlap_audit(),field_balance=sim.fields.audit,
                  scope=episode["scope"])
    write_json(path.with_name(path.name.replace(".luad2.json.gz",".report.json")),report)
    return sim


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--atlas",default=str(ROOT/"outputs/atlas_B26.json.gz"))
    ap.add_argument("--contract",default=str(ROOT/"contracts/runtime-v2-calibrated.json"))
    ap.add_argument("--scenarios",default="S0,S1,S5")
    ap.add_argument("--seeds",default="21")
    ap.add_argument("--hours",type=int,default=72)
    ap.add_argument("--out",type=Path,default=ROOT/"outputs/autonomous")
    ap.add_argument("--live",action="store_true")
    ap.add_argument("--max-requests",type=int)
    ap.add_argument("--model",default="jev-1.13.0")
    ap.add_argument("--resume",action="store_true")
    args = ap.parse_args()
    contract,atlas = read_json(args.contract),read_json(args.atlas)
    if not 1 <= args.hours <= contract["run"]["max_horizon_min"]//60: ap.error("Hours must be 1–168")
    if args.live and (not args.max_requests or args.max_requests < 1): ap.error("Live mode requires a positive total --max-requests")
    if args.resume and not args.live: ap.error("Resume uses a live-response journal; local runs are reproducible from the seed")
    if args.live and (len(args.scenarios.split(",")) != 1 or len(args.seeds.split(",")) != 1): ap.error("One live scenario/seed per capped journal")
    contract["run"]["horizon_min"] = args.hours*60
    args.out.mkdir(parents=True,exist_ok=True)
    for scenario in args.scenarios.split(","):
        for seed in map(int,args.seeds.split(",")):
            name = f"{atlas['patch_id']}-{scenario}-seed{seed}-{args.hours}h"
            local_path = args.out/f"{name}-local.luad2.json.gz"
            local = record(atlas,copy.deepcopy(contract),scenario,seed,local_path)
            print(f"Local estimate: {len(local.decisions)} questions in {local.summary()['estimated_requests']} requests. This is not a prediction of Jev's trajectory.",flush=True)
            if args.live:
                key = os.environ.get("TYPESAFE_API_KEY")
                if not key: ap.error("Set this project's TYPESAFE_API_KEY in the process environment")
                journal = args.out/f"{name}-jev.audit.jsonl"
                if journal.exists() and not args.resume: ap.error("Journal exists; use --resume to reuse it without repaying")
                context = dict(atlas=atlas["fingerprint"],contract=fingerprint(contract),engine=engine_fingerprint(),scenario=scenario,seed=seed)
                provider = BatchedJevProvider(key,args.model,args.max_requests,contract["provider"],journal,run_context=context)
                record(atlas,copy.deepcopy(contract),scenario,seed,args.out/f"{name}-jev.luad2.json.gz",provider)


if __name__ == "__main__": main()
