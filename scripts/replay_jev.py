"""Reconstruct a recorded kernel from cached Jev replies with transport disabled."""
import argparse,sys,time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from luad_tissue.io import fingerprint,read_json,write_json
from luad_tissue.v2.autonomous import AutonomousSimulation
from luad_tissue.v2.episode import engine_fingerprint,validate_episode
from luad_tissue.v2.provider_jev import BatchedJevProvider


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--episode',type=Path,required=True);p.add_argument('--journal',type=Path,required=True)
    p.add_argument('--atlas',type=Path,default=ROOT/'outputs/atlas_B26.json.gz')
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();original,atlas=read_json(args.episode),read_json(args.atlas)
    validate_episode(original,atlas)
    if original['engine_fingerprint']!=engine_fingerprint():raise SystemExit('Engine changed; preserve the original recording')
    if not args.journal.is_file():raise SystemExit('Existing paid-response journal required')
    def forbidden(_):raise AssertionError('Network transport is disabled during reconstruction')
    context=dict(atlas=atlas['fingerprint'],contract=fingerprint(original['contract']),engine=engine_fingerprint(),scenario=original['scenario'],seed=original['seed'])
    before=args.journal.read_bytes()
    policy=BatchedJevProvider('reconstruction-without-credentials',original['contract']['provider']['pinned_model'],
        original['paid_calls'],original['contract']['provider'],args.journal,transport=forbidden,run_context=context)
    sim=AutonomousSimulation(atlas,original['contract'],original['scenario'],original['seed'],policy)
    last=-1;start=time.perf_counter()
    while not sim.stop_reason:
        sim.step()
        if sim.time//360!=last or sim.stop_reason:
            sim.episode();last=sim.time//360
            print(f'Reconstructed {sim.time/60:g} h from cached replies; no transport available.',flush=True)
    replay=sim.episode()
    if args.journal.read_bytes()!=before:raise AssertionError('Reconstruction changed the paid journal')
    for key in ('decisions','events','metrics','bodies','frames','final_state','final_state_fingerprint'):
        if replay[key]!=original[key]:raise AssertionError('Reconstructed '+key+' differs')
    if replay['summary']['stop_reason']!=original['summary']['stop_reason']:raise AssertionError('Stop reason differs')
    write_json(args.output,dict(verified=True,modeled_hours=sim.time/60,new_http_requests=0,
        journal_unchanged=True,matched=['decisions','events','metrics','bodies','frames','final_state'],
        final_state_fingerprint=replay['final_state_fingerprint'],original_episode_fingerprint=original['fingerprint'],
        engine_fingerprint=engine_fingerprint(),seconds=round(time.perf_counter()-start,2),
        note='Provider cache flags are reconstruction provenance; original paid receipts remain unchanged.'))
    print('Exact biological reconstruction verified; zero new HTTP requests.',flush=True)


if __name__=='__main__':main()
