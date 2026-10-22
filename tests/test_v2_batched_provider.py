import copy
import json
from pathlib import Path

import pytest

from luad_tissue.io import read_json
from luad_tissue.providers import BudgetExhausted
from luad_tissue.v2.provider_jev import BatchedJevProvider,build_batches,normalize_answer

P = read_json(Path(__file__).resolve().parents[1]/"contracts/runtime-v2.json")["provider"]


def requests(n=21):
    return [dict(cell_id=i,options={"REST":dict(description="Rest"),"SCAN":dict(description="Scan")},observation=dict(time_min=0,local_signal_sim=.1)) for i in range(n)]


def response(body):
    return dict(model="jev-test-pinned",usage=dict(input_tokens=100,output_tokens=30),answers={k:dict(type="choice",choice="REST",probabilities={"REST":.6,"SCAN":.4},confidence=.8) for k in body["questions"]})


def test_batches_have_question_and_byte_limits():
    rs = requests(47)
    assert list(map(len,build_batches(rs,"test",P))) == [20,20,7]
    p = {**P,"max_payload_bytes":1700}
    assert len(build_batches(rs,"test",p)) > 3
    with pytest.raises(ValueError): build_batches(rs,"test",{**p,"max_payload_bytes":10})


def test_rounded_probabilities_and_small_argmax_gap_are_audited():
    answer = dict(type="choice",choice="a",probabilities={"a":.33,"b":.34,"c":.34},confidence=.8)
    normalized = normalize_answer(answer,{"a":1,"b":1,"c":1},P)
    assert normalized["choice"] == "b"
    assert sum(normalized["probabilities"].values()) == pytest.approx(1)
    assert set(normalized["repairs"]) == {"rounded_sum_normalized","small_argmax_gap"}
    answer["probabilities"] = {"a":.3,"b":.4,"c":.3}
    with pytest.raises(ValueError): normalize_answer(answer,{"a":1,"b":1,"c":1},P)


def test_invalid_cell_does_not_discard_valid_peers(tmp_path):
    def mixed(body):
        result = response(body)
        result["answers"]["c0"]["probabilities"]["REST"] = float("nan")
        # JSON transport must be finite; use a bad but serializable answer.
        result["answers"]["c0"]["probabilities"]["REST"] = -1
        return result
    p = BatchedJevProvider("test-key","test",1,P,tmp_path/"audit.jsonl",mixed)
    answers = p.choose(requests(2))
    assert set(answers) == {1}
    assert p.audit[0]["validation"]["0"]["status"] == "invalid"


def test_round_budget_precheck_and_resume_without_repayment(tmp_path):
    calls = []
    def transport(body):
        calls.append(body)
        return response(body)
    path = tmp_path/"audit.jsonl"
    p = BatchedJevProvider("test-key","test",1,P,path,transport)
    with pytest.raises(BudgetExhausted): p.choose(requests(21))
    assert not calls and not path.exists()
    p.limit = 2
    first = p.choose(requests(21))
    assert len(calls) == 2
    resumed = BatchedJevProvider("test-key","test",2,P,path,transport)
    assert resumed.choose(requests(21)) == first
    assert len(calls) == 2 and resumed.requests == 2
    assert all(a["cached"] for a in resumed.audit)
    assert "test-key" not in path.read_text()


def test_unknown_intent_is_not_repaid_and_failures_are_redacted(tmp_path):
    def failure(body): raise RuntimeError("fixture secret-key")
    path = tmp_path/"audit.jsonl"
    p = BatchedJevProvider("secret-key","test",1,P,path,failure)
    assert p.choose(requests(1)) == {}
    assert "secret-key" not in path.read_text()
    # Model a crash between a durably written intent and its result.
    line = path.read_text().splitlines()[0]
    path.write_text(line+"\n")
    def forbidden(body): pytest.fail("An uncertain paid request must never be sent again")
    resumed = BatchedJevProvider("secret-key","test",1,P,path,forbidden)
    assert resumed.choose(requests(1)) == {}
    assert resumed.requests == 1


def test_changed_returned_model_and_nonfinite_confidence_are_rejected(tmp_path):
    returned = iter(["a","b"])
    def transport(body):
        data = response(body)
        data["model"] = next(returned)
        return data
    p = BatchedJevProvider("key","test",2,P,tmp_path/"audit.jsonl",transport)
    answers = p.choose(requests(21))
    assert len(answers) == 20 and 20 not in answers
    a = response({"questions":{"x":{}}})["answers"]["x"]
    a["confidence"] = float("inf")
    with pytest.raises(ValueError): normalize_answer(a,{"REST":1,"SCAN":1},P)
