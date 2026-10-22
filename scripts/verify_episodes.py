"""Run all available measured geometries through local-policy controls; no API."""
import sys
from pathlib import Path
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from luad_tissue.engine import Simulation
from luad_tissue.io import read_json,write_json


def main():
    rb=read_json(ROOT/"rulebook/rulebook.json")
    contract=read_json(ROOT/"contracts/runtime-v1.json")
    results=[]
    for region in (26,27):
        path=ROOT/f"outputs/atlas_B{region}.json.gz"
        if not path.exists():continue
        atlas=read_json(path)
        for scenario in contract["scenarios"]:
            sim=Simulation(atlas,rb,contract,scenario)
            while not sim.stop_reason:sim.step()
            sim.check_invariants()
            if scenario in ("baseline","recognition_off"):
                assert not sim.events and not sim.decisions
            if scenario=="cognate":
                write_json(ROOT/f"outputs/examples/B{region}-cognate.luad.json.gz",sim.episode())
            result=dict(region=region,scenario=scenario,final={k:v for k,v in sim.snapshot().items() if k!="cells"},
                        events=dict(Counter(e["kind"] for e in sim.events)),episode_fingerprint=sim.episode()["fingerprint"])
            results.append(result)
            print(region,scenario,result["final"]["counts"],"decisions",len(sim.decisions),flush=True)
    if not results:raise SystemExit("Build an atlas before checking real-region episodes")
    write_json(ROOT/"outputs/episode-verification.json",dict(provider="local_policy",paid_calls=0,results=results))


if __name__=="__main__":main()
