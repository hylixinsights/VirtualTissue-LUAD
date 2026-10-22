import copy
import pytest
from luad_tissue.engine import Simulation, LocalPolicy, validate_answer
from luad_tissue.providers import BudgetExhausted
from luad_tissue.io import fingerprint


def finish(sim):
    while not sim.stop_reason:sim.step()
    return sim


@pytest.mark.parametrize("scenario",["baseline","recognition_off"])
def test_negative_controls_stay_quiet(atlas,rulebook,contract,scenario):
    sim=finish(Simulation(atlas,rulebook,contract,scenario))
    assert not sim.decisions and not sim.events
    assert all(s["viability"]=="alive" for s in sim.state.values())


def test_timed_damage_death_clearance_and_finite_material(atlas,rulebook,contract):
    original=copy.deepcopy(atlas)
    sim=Simulation(atlas,rulebook,contract,"cognate")
    assert not any("efferocytose" in k for r in sim.requests() for k in r["options"])
    sim.step()
    assert sim.state[2]["damage_au"]==0
    sim.step()
    assert sim.state[2]["damage_au"]==1
    sim=finish(sim)
    kinds=[e["kind"] for e in sim.events]
    assert "apoptosis_committed" in kinds and "death_completed" in kinds and "target_cleared" in kinds
    assert sim.state[2]["viability"]=="cleared"
    assert sim.spent_pulses==2
    assert atlas==original
    sim.check_invariants()


def test_contact_loss_cancels_program(atlas,rulebook,contract):
    sim=Simulation(atlas,rulebook,contract,"cognate")
    sim.step();atlas["cells"][0]["contacts"]=[];sim.step()
    assert sim.state[2]["damage_au"]==0
    assert sim.events[-1]["kind"]=="program_cancelled"


def test_busy_cell_report_withholds_a_second_program(atlas,rulebook,contract):
    sim=Simulation(atlas,rulebook,contract,"cognate");sim.step()
    report=next(r for r in sim.report(1) if r["rule_id"].startswith("CD8_"))
    assert report["result"]=="false"
    assert any(c["path"]=="runtime.actor_unoccupied" and c["result"]=="false" for c in report["checks"])


def test_boundary_targets_never_receive_damage(atlas,rulebook,contract):
    atlas["cells"][1]["role"]="halo";atlas["summary"]["n_roi"]=2
    sim=finish(Simulation(atlas,rulebook,contract,"cognate"))
    assert not sim.decisions


def test_checkpoint_is_disclosed_multiplier_not_probability(atlas,rulebook,contract):
    inhibitory=finish(Simulation(atlas,rulebook,contract,"checkpoint"))
    blockade=finish(Simulation(atlas,rulebook,contract,"blockade"))
    assert inhibitory.state[2]["damage_au"]==.75
    assert inhibitory.state[2]["viability"]=="alive"
    assert blockade.state[2]["viability"]=="cleared"


def test_seeded_reproducibility(atlas,rulebook,contract):
    first=finish(Simulation(atlas,rulebook,contract,"cognate",7)).episode()
    second=finish(Simulation(atlas,rulebook,contract,"cognate",7)).episode()
    assert first["fingerprint"]==second["fingerprint"]


def test_invalid_response_starts_no_program_but_clocks_advance(atlas,rulebook,contract):
    class Invalid:
        name="invalid_fixture"
        def choose(self,rows):return {r["cell_id"]:dict(choice="invented") for r in rows}
    sim=Simulation(atlas,rulebook,contract,"cognate",provider=Invalid());sim.step()
    assert sim.time==10 and sim.failures
    assert not sim.events and sim.state[2]["damage_au"]==0
    assert all(d["receipt"]=="provider_failure" for d in sim.decisions)


def test_budget_stops_without_new_time_or_decisions(atlas,rulebook,contract):
    class Limited:
        name="budget_fixture"
        def choose(self,rows):raise BudgetExhausted("no budget")
    sim=Simulation(atlas,rulebook,contract,"cognate",provider=Limited());sim.step()
    assert sim.time==0 and not sim.decisions
    assert sim.stop_reason=="request_budget_exhausted"


@pytest.mark.parametrize("probabilities",[{"wait":float("nan")},{"wait":True},{"wait":.5},{"wait":1,"other":0}])
def test_bad_probabilities_rejected(probabilities):
    with pytest.raises(ValueError):validate_answer(dict(choice="wait",probabilities=probabilities,confidence=1),{"wait":{}})


def test_episode_fingerprint_covers_every_decision(atlas,rulebook,contract):
    data=finish(Simulation(atlas,rulebook,contract,"cognate")).episode()
    claimed=data.pop("fingerprint");assert fingerprint(data)==claimed
    data["decisions"][0]["receipt"]="tampered"
    assert fingerprint(data)!=claimed
