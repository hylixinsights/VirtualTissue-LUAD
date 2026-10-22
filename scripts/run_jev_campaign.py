"""Run a capped paid pilot, pause for inspection, then reuse it for a full run.

The key enters only via the process environment or a hidden terminal prompt.
A whole-campaign ledger reserves every external attempt before transport.
No automatic retries or automatic acceptance of a concentrated pilot.
"""
import argparse,copy,getpass,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from luad_tissue.io import read_json,write_json,fingerprint
from luad_tissue.v2.campaign import CampaignBudget
from luad_tissue.v2.episode import engine_fingerprint,validate_episode
from luad_tissue.v2.provider_jev import BatchedJevProvider
from run_autonomous import record


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--live',action='store_true',required=True)
    p.add_argument('--max-campaign-requests',type=int,required=True)
    p.add_argument('--max-run-requests',type=int,required=True)
    p.add_argument('--campaign',type=Path,required=True)
    p.add_argument('--contract',type=Path,required=True)
    p.add_argument('--atlas',type=Path,default=ROOT/'outputs/atlas_B26.json.gz')
    p.add_argument('--scenario',default='S1');p.add_argument('--seed',type=int,default=21)
    p.add_argument('--hours',type=int,default=72);p.add_argument('--prompt-key',action='store_true')
    p.add_argument('--dry-episode',type=Path,help='Reuse an already completed, exactly matching local control')
    args=p.parse_args()
    if not 1<=args.hours<=168 or args.max_run_requests<1:p.error('Positive run cap and 1–168 hours required')
    budget=CampaignBudget(args.campaign,args.max_campaign_requests)
    contract,atlas=read_json(args.contract),read_json(args.atlas)
    contract['run']['horizon_min']=args.hours*60
    args.campaign.mkdir(parents=True,exist_ok=True)
    stem=f"{atlas['patch_id']}-{args.scenario}-seed{args.seed}-{args.hours}h-calibrated"
    print('Local dry-run estimate before live inference.',flush=True)
    if args.dry_episode:
        dry=read_json(args.dry_episode);validate_episode(dry,atlas)
        if not (dry.get('engine_fingerprint')==engine_fingerprint() and fingerprint(dry['contract'])==fingerprint(contract)
                and dry['seed']==args.seed and dry['scenario']==args.scenario and dry['provider']=='local_policy_v2'
                and dry['summary']['stop_reason']=='horizon_reached' and dry['summary']['time_min']==args.hours*60):
            raise SystemExit('Dry control does not exactly match this engine, contract and experiment')
        estimate=dry['summary']['estimated_requests']
    else:
        dry=record(atlas,copy.deepcopy(contract),args.scenario,args.seed,args.campaign/(stem+'-local.luad2.json.gz'))
        estimate=dry.summary()['estimated_requests']
    print('Dry-run requests:',estimate,'; existing campaign attempts:',len(budget.entries()),flush=True)
    remaining=budget.limit-len(budget.entries())
    if remaining<1:raise SystemExit('Campaign budget exhausted; no network call')
    key=getpass.getpass('LUAD key (hidden input): ') if args.prompt_key else os.environ.get('TYPESAFE_API_KEY')
    if not key:raise SystemExit('Missing process key; nothing sent')
    context=dict(atlas=atlas['fingerprint'],contract=fingerprint(contract),engine=engine_fingerprint(),scenario=args.scenario,seed=args.seed)
    journal=args.campaign/(stem+'-jev.audit.jsonl')
    # This runner is the sole live process in its campaign; the global ledger
    # remains authoritative even if another process attempts to share it.
    already=sum(1 for row in journal.read_text().splitlines() if '"phase":"intent"' in row) if journal.exists() else 0
    cap=min(args.max_run_requests,remaining+already)
    def provider():
        obj=BatchedJevProvider(key,'jev-1.13.0',cap,contract['provider'],journal,run_context=context)
        obj.transport=budget.wrap(obj._remote,stem)
        return obj
    live=record(atlas,copy.deepcopy(contract),args.scenario,args.seed,args.campaign/(stem+'-pilot.luad2.json.gz'),provider())
    print('PILOT:',live.stop_reason,'; decisions:',len(live.decisions),'; invalid:',len(live.failures),'; campaign attempts:',len(budget.entries()),flush=True)
    if live.stop_reason=='pilot_review_decision_concentration' and len(live.failures)/max(1,len(live.decisions))<=.1:
        decision=input('Inspect the pilot, then type continue-reviewed to reuse its journal without repayment: ')
        if decision.strip()=='continue-reviewed':
            if engine_fingerprint()!=context['engine']:raise SystemExit('Engine changed during pilot review; preserve journal and stop')
            write_json(args.campaign/(stem+'-review.json'),dict(reviewed_concentration=True,
                rationale='Reviewed cell-type distribution and valid local menus; retain cell/day caps. Question shares follow local eligibility and independent checkpoints, not tissue composition.',
                decisions_by_type=live.summary()['decisions_by_type'],
                invalid_fraction=len(live.failures)/max(1,len(live.decisions)),campaign_attempts_at_review=len(budget.entries())))
            live=record(atlas,copy.deepcopy(contract),args.scenario,args.seed,args.campaign/(stem+'-jev.luad2.json.gz'),provider(),reviewed_concentration=True)
    write_json(args.campaign/'campaign-status.json',dict(limit=budget.limit,attempts=len(budget.entries()),remaining=budget.limit-len(budget.entries()),
                final_stop=live.stop_reason,hours=live.time/60,run_requests=getattr(live.policy,'requests',0),decisions=len(live.decisions),invalid=len(live.failures)))
    print('CAMPAIGN:',len(budget.entries()),'/',budget.limit,'attempts;',live.stop_reason,live.time/60,'modeled hours.',flush=True)
    key=None


if __name__=='__main__':main()
