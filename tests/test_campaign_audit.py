import importlib.util
from pathlib import Path
import pytest
from luad_tissue.io import fingerprint,write_json
from luad_tissue.v2.campaign import CampaignBudget
from luad_tissue.v2.provider_jev import BatchedJevProvider
from test_v2_fields_programs import sim

ROOT=Path(__file__).resolve().parents[1]


def auditor():
    spec=importlib.util.spec_from_file_location('campaign_audit_test',ROOT/'scripts/audit_jev_campaign.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module.audit


def make_recording(sim,tmp_path):
    def synthetic(body):
        answers={}
        for key,q in body['questions'].items():
            choices=list(q['criteria']);choice=choices[0]
            answers[key]=dict(type='choice',choice=choice,confidence=1.,probabilities={c:float(c==choice) for c in choices})
        return dict(model='jev-test-pinned',answers=answers,usage=dict(input_tokens=100,output_tokens=10))
    budget=CampaignBudget(tmp_path,5000)
    sim.policy=BatchedJevProvider('synthetic-only','jev-test-pinned',4999,sim.contract['provider'],
        tmp_path/'sample-jev.audit.jsonl',transport=budget.wrap(synthetic,'fixture'))
    episode=sim.run(30).episode();path=tmp_path/'sample-jev.luad2.json.gz';atlas=tmp_path/'atlas.json.gz'
    write_json(path,episode);write_json(atlas,sim.atlas)
    return episode,path,atlas


def test_audit_links_each_decision_to_a_paid_receipt(sim,tmp_path):
    episode,path,atlas=make_recording(sim,tmp_path)
    result=auditor()(tmp_path,path,atlas)
    assert result['verified'] and result['questions']==len(episode['decisions'])
    assert result['cumulative_requests']==episode['paid_calls']
    assert result['usage']['input_tokens']==episode['paid_calls']*100


def test_refingerprinted_decision_cannot_claim_a_different_provider_answer(sim,tmp_path):
    episode,path,atlas=make_recording(sim,tmp_path)
    episode['decisions'][0]['answer']['confidence']=.123
    episode['fingerprint']=fingerprint({k:v for k,v in episode.items() if k!='fingerprint'})
    write_json(path,episode)
    with pytest.raises(ValueError,match='exact validated provider receipt'):auditor()(tmp_path,path,atlas)
