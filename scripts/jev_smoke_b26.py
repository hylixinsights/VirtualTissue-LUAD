"""A single smoke batch from current kernel-validated B26 menus. Dry run by default.

--live requests a paid call, with a key from the process environment and an
explicit cap. Responses are journaled and reused, never automatically repaid.
No returned decision is applied to the tissue.
"""
import argparse
import os
import sys
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from luad_tissue.io import canonical,fingerprint,read_json,write_json
from luad_tissue.v2.autonomous import AutonomousSimulation
from luad_tissue.v2.episode import engine_fingerprint
from luad_tissue.v2.provider_jev import BatchedJevProvider,build_batches,payload


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--live",action="store_true")
    p.add_argument("--max-requests",type=int)
    p.add_argument("--questions",type=int,default=20)
    p.add_argument("--model",default="jev-1.13.0")
    p.add_argument("--atlas",default=str(ROOT/"outputs/atlas_B26.json.gz"))
    args=p.parse_args()
    if args.live and args.max_requests is None:p.error("Live mode requires an explicit --max-requests cap")
    if (args.max_requests is not None and not 1<=args.max_requests<=10) or not 1<=args.questions<=20:p.error("Request cap must be 1-10 and questions 1-20")
    atlas,contract=read_json(args.atlas),read_json(ROOT/"contracts/runtime-v2.json")
    sim=AutonomousSimulation(atlas,contract,"S1",21)
    groups=defaultdict(list)
    for row in sim.requests():groups[row["observation"]["primary_label"]].append(row)
    rows=[]
    while len(rows)<args.questions and any(groups.values()):
        for label in sorted(groups):
            if groups[label] and len(rows)<args.questions:rows.append(groups[label].pop(0))
    rows=build_batches(rows,args.model,contract["provider"])[0]
    body=payload(rows,args.model)
    digest=fingerprint(body)
    out=ROOT/"outputs/jev_smoke"
    write_json(out/f"validated-request-{digest[:12]}.json",body)
    print(f"Dry-run estimate: one request, {len(rows)} kernel-validated questions, {len(canonical(body))} payload bytes.",flush=True)
    if not args.live:
        print("Nothing sent; zero paid calls.")
        return
    key=os.environ.get("TYPESAFE_API_KEY")
    if not key:p.error("Set this project's TYPESAFE_API_KEY in the process environment")
    provider=BatchedJevProvider(key,args.model,args.max_requests,contract["provider"],out/f"smoke-{digest[:12]}.audit.jsonl",
                                run_context=dict(smoke=True,atlas=atlas["fingerprint"],contract=fingerprint(contract),engine=engine_fingerprint()))
    answers=provider.choose(rows)
    report=dict(request_hash=digest,questions=len(rows),valid_answers=len(answers),calls_total=provider.requests,audit=provider.audit,
                scope="Connection/protocol smoke only; no answer applied to tissue.")
    write_json(out/f"validated-response-{digest[:12]}.json",report)
    print(f"Validated {len(answers)}/{len(rows)} answers; {provider.requests} journaled requests. No automatic retry.")


if __name__=="__main__":main()
