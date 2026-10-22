import pytest
from luad_tissue.engine import Simulation
from luad_tissue.providers import JevProvider, BudgetExhausted


def response(payload):
    opts=payload["questions"]["behavior"]["criteria"]
    return dict(model="jev-test-pinned",answers=dict(behavior=dict(type="choice",choice="wait",probabilities={k:float(k=="wait") for k in opts},confidence=1)),usage=dict(input_tokens=10,output_tokens=2))


def test_one_request_per_cell_and_budget(atlas,rulebook,contract):
    rows=Simulation(atlas,rulebook,contract,"cognate").requests()
    provider=JevProvider("synthetic-secret","jev-test-pinned",1,transport=response)
    assert provider.choose(rows)[1]["choice"]=="wait"
    assert provider.requests==1
    with pytest.raises(BudgetExhausted):provider.choose(rows)
    assert provider.requests==1
    assert "synthetic-secret" not in str(provider.audit)


def test_failed_request_is_counted_without_retry(atlas,rulebook,contract):
    calls=[]
    def failing(payload):calls.append(payload);raise TimeoutError()
    provider=JevProvider("synthetic-secret","jev-test-pinned",10,transport=failing)
    with pytest.raises(RuntimeError):provider.choose(Simulation(atlas,rulebook,contract,"cognate").requests())
    assert len(calls)==provider.requests==1
    assert provider.audit[0]["usage"]=="unknown"


def test_alias_model_not_allowed():
    with pytest.raises(ValueError):JevProvider("synthetic","jev-latest",10)


def test_model_change_rejected(atlas,rulebook,contract):
    provider=JevProvider("synthetic","jev-test-pinned",10,transport=response)
    rows=Simulation(atlas,rulebook,contract,"cognate").requests();provider.choose(rows)
    provider.transport=lambda p:{**response(p),"model":"changed"}
    with pytest.raises(RuntimeError):provider.choose(rows)
