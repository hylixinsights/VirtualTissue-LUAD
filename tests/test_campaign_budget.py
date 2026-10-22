import pytest
from luad_tissue.v2.campaign import CampaignBudget
from luad_tissue.providers import BudgetExhausted

def test_campaign_cap_survives_restart_and_counts_failed_transport(tmp_path):
    budget=CampaignBudget(tmp_path,2)
    calls=[]
    def fail(body):calls.append(body);raise RuntimeError('test failure')
    with pytest.raises(RuntimeError):budget.wrap(fail,'smoke')({'x':1})
    resumed=CampaignBudget(tmp_path,2)
    resumed.wrap(calls.append,'pilot')({'x':2})
    with pytest.raises(BudgetExhausted):resumed.wrap(calls.append,'extra')({'x':3})
    assert len(calls)==2 and len(resumed.entries())==2
    with pytest.raises(ValueError):CampaignBudget(tmp_path,3)

def test_campaign_lock_fails_closed(tmp_path):
    budget=CampaignBudget(tmp_path,3)
    budget.lock.touch()
    with pytest.raises(RuntimeError,match='locked'):budget.reserve({},'test')
    assert not budget.entries()
