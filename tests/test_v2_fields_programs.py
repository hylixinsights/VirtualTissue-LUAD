import copy
from pathlib import Path

import numpy as np
import pytest

from luad_tissue.io import fingerprint,read_json
from luad_tissue.v2.autonomous import AutonomousSimulation
from luad_tissue.v2.fields import FieldGrid
from luad_tissue.v2.menus import menu
from luad_tissue.v2.scheduler import WakeScheduler
from v2_synthetic import synthetic_atlas

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def sim():
    c = read_json(ROOT/"contracts/runtime-v2.json")
    c["run"]["horizon_min"] = 120
    c["geometry"]["fit_iterations"] = 20
    return AutonomousSimulation(synthetic_atlas(n=9,roi_radius=22),c,"S1",4)


def test_constant_solution_mass_balance_and_conservative_deposition():
    g = FieldGrid([0,0,40,40],2,{"x":dict(diffusion=30.,decay=.1)})
    source = np.full(g.shape,.2)
    assert np.allclose(g.solve("x",source),2,atol=1e-10)
    assert abs(g.audit["x"]["balance_error"]) < 1e-9
    xy = [[.5,.25],[13.2,4.6],[39.9,39.9]]
    deposited = g.deposit(xy,[3,4,5])
    assert deposited.sum()*g.spacing**2 == pytest.approx(12.)
    assert np.allclose(g.sample("x",xy),2)
    assert abs(g.gradient("x",xy)).max() < 1e-10


def test_single_line_source_has_expected_decay_length():
    g = FieldGrid([0,0,400,4],1,{"x":dict(diffusion=10.,decay=.1)})
    source = np.zeros(g.shape)
    source[:,200] = 1
    c = g.solve("x",source)[2]
    observed_length = -30/np.log(c[250]/c[220])
    assert observed_length == pytest.approx(np.sqrt(10/.1),rel=.01)
    assert abs(g.audit["x"]["balance_error"]) < 1e-8


def test_scheduler_keeps_quiet_cells_unqueried_and_caps_each_day():
    s = WakeScheduler(dict(max_per_cell_day=2,interval_min={"T_CD8_cytotoxic":60},cd8_contact_interval_min=30))
    assert not s.eligible(1,0)
    s.wake(1,"contact")
    assert s.eligible(1,0)
    s.consume(1,0,"T_CD8_cytotoxic")
    s.wake(1,"completed")
    assert not s.eligible(1,59)
    s.consume(1,60,"T_CD8_cytotoxic")
    s.wake(1,"completed")
    assert not s.eligible(1,1400)
    assert s.eligible(1,1440)


def contact_action(sim,action):
    for g in range(len(sim.bio)):
        if not sim.tissue.acts[g]: continue
        options,_ = menu(sim,g)
        for option in options.values():
            if option["action"] == action: return g,option
    pytest.fail(f"No {action} option in fixture")


def test_unknown_recognition_withheld_but_declared_contact_consumes_material(sim):
    g,o = contact_action(sim,"DEGRANULATE")
    sim.scenario["recognition"] = None
    options,excluded = menu(sim,g)
    assert not any(k.startswith("DEGRANULATE") for k in options)
    assert any(c["result"] == "unknown" for k,v in excluded.items() if k.startswith("DEGRANULATE") for c in v)
    sim.scenario["recognition"] = True
    sim.start(g,o)
    sim.time = sim.p["contact_program_min"]
    before = sim.bio[g]["pulses"]
    sim.complete_programs()
    assert sim.bio[g]["pulses"] == before-1
    assert sim.bio[o["target_index"]]["damage_au"] > 0


def test_lost_contact_cancels_without_spending_pulse(sim):
    g,o = contact_action(sim,"DEGRANULATE")
    sim.start(g,o)
    sim.graph.pop(tuple(sorted((g,o["target_index"]))))
    sim.time = sim.p["contact_program_min"]
    before = sim.bio[g]["pulses"]
    sim.complete_programs()
    assert sim.bio[g]["pulses"] == before
    assert sim.events[-1]["kind"] == "program_cancelled"


def test_metabolic_shift_is_individual_and_completes_on_clock(sim):
    g,o = contact_action(sim,"GLYCOLYTIC_SHIFT")
    before = [s["glycolysis"] for s in sim.bio]
    sim.start(g,o)
    sim.complete_programs()
    assert [s["glycolysis"] for s in sim.bio] == before
    sim.time += sim.p["program_min"]
    sim.complete_programs()
    assert sim.bio[g]["glycolysis"] == before[g]+sim.p["glycolysis_step"]
    assert all(s["glycolysis"] == before[k] for k,s in enumerate(sim.bio) if k != g)


def test_death_and_necrosis_are_kernel_clocks_and_accounted(sim):
    g,o = contact_action(sim,"GLYCOLYTIC_SHIFT")
    sim.commit_death(g,"fixture")
    assert sim.accounting()["acting"]["apoptosis_committed"] == 1
    sim.time = sim.p["death_commitment_min"]
    sim.advance_biology(10)
    assert sim.bio[g]["viability"] == "dead_intact"
    assert sim.accounting()["acting"]["dead_intact"] == 1
    other = next(k for k in range(len(sim.bio)) if sim.tissue.acts[k] and sim.tissue.labels[k].startswith("Tumor") and k != g)
    sim.local_fields[other]["oxygen"] = 0
    sim.bio[other]["hypoxia_min"] = sim.p["necrosis_delay_min"]-10
    sim.advance_biology(10)
    assert sim.bio[other]["viability"] == "necrotic"
    assert not sim.tissue.present[other]
    sim.tissue.check_invariants()


def test_static_fields_do_not_move_cells_and_baseline_oxygen_is_high(sim):
    c = copy.deepcopy(sim.contract)
    quiet = AutonomousSimulation(sim.atlas,c,"static",4).run(60)
    assert np.array_equal(quiet.tissue.xy,quiet.tissue.xy0)
    assert not quiet.decisions and not quiet.events
    assert quiet.metrics[-1]["hypoxic_tumour_fraction"] == 0
    assert quiet.metrics[-1]["field_balance_max"] < 1e-7


def test_reproducible_full_episode_and_no_context_decisions(sim):
    e1 = sim.run(120).episode()
    e2 = AutonomousSimulation(sim.atlas,sim.contract,"S1",4).run(120).episode()
    assert e1["fingerprint"] == e2["fingerprint"]
    assert e1["final_state_fingerprint"] == fingerprint(e1["final_state"])
    context = {c["cell_id"] for c in sim.atlas["cells"] if c["role"] != "roi"}
    assert not context.intersection(d["cell_id"] for d in e1["decisions"])
    assert all(d["observation"]["primary_label"] not in ("B_cell","Plasma_cell") for d in e1["decisions"])
    assert e1["paid_calls"] == 0


def relabel(sim,g,label):
    sim.tissue.labels[g] = label
    cell = sim.by_id[int(sim.tissue.ids[g])]
    cell["identity"]["candidates"] = [dict(label=label,lineage="SIM_fixture",source="fixture")]


def test_clearance_is_contact_bound_finite_and_cannot_happen_twice(sim):
    g,o = contact_action(sim,"DEGRANULATE")
    k = o["target_index"]
    relabel(sim,g,"Macrophage_SPP1")
    sim.commit_death(k,"fixture")
    options,_ = menu(sim,g)
    clear = next(v for v in options.values() if v["action"] == "EFFEROCYTOSE")
    sim.start(g,clear)
    sim.time = sim.p["clearance_min"]
    sim.complete_programs()
    assert sim.bio[g]["processed"] == 1
    assert sim.bio[k]["viability"] == "cleared" and not sim.tissue.present[k]
    sim.bio[g]["program"] = dict(action="EFFEROCYTOSE",target=k,start=0,due=0)
    sim.complete_programs()
    assert sim.bio[g]["processed"] == 1
    assert sim.accounting()["acting"]["cleared"] == 1


def test_cd4_help_licenses_cycle_and_division_partitions_pulses(sim):
    g,o = contact_action(sim,"DEGRANULATE")
    k = o["target_index"]
    relabel(sim,k,"T_CD4")
    sim.bio[g]["last_stimulation"] = 0
    sim.bio[g]["exhaustion"] = .2
    options,_ = menu(sim,k)
    help_option = next(v for v in options.values() if v["action"] == "HELP_CD8" and v["target_index"] == g)
    sim.start(k,help_option)
    sim.time = sim.p["program_min"]
    sim.complete_programs()
    assert sim.bio[g]["exhaustion"] == pytest.approx(.12)
    options,_ = menu(sim,g)
    sim.start(g,options["PROLIFERATE"])
    sim.time += sim.p["cd8_cycle_min"]
    before = sim.bio[g]["pulses"]
    sim.advance_autonomous_cycles()
    assert sim.tissue.born == 1
    assert sim.bio[g]["pulses"]+sim.bio[-1]["pulses"] == before
    assert sim.bio[g]["cycle"] is None


@pytest.mark.parametrize("action,field,label",[("SECRETE_CXCL9","cxcl9","Macrophage_SPP1"),("SECRETE_VEGFA_TGFB","tgfb","Macrophage_SPP1"),("SECRETE_TGFB","tgfb","CAF"),("SECRETE_VEGFA","vegf","CAF"),("DEPOSIT_MATRIX","matrix","CAF")])
def test_secretory_programs_have_local_field_sources(sim,action,field,label):
    g,o = contact_action(sim,"DEGRANULATE")
    relabel(sim,g,label)
    sim.start(g,dict(action=action,target_index=None))
    sim.update_fields()
    assert sim.fields.values[field].max() > 0
    sim.time = sim.p["secretory_program_min"]
    sim.complete_programs()
    if label == "Macrophage_SPP1":
        assert sim.bio[g]["polarized_until"] > sim.time
    if field == "matrix":
        before = sim.fields.values[field].sum()
        sim.update_fields()
        assert 0 < sim.fields.values[field].sum() < before


def test_sprout_requires_new_connection_and_perfusion_delay(sim):
    g,o = contact_action(sim,"DEGRANULATE")
    k = o["target_index"]
    relabel(sim,g,"Endothelial")
    relabel(sim,k,"Endothelial")
    sim.bio[g]["perfused"] = sim.bio[k]["perfused"] = True
    sim.start(g,dict(action="SPROUT",target_index=None))
    assert not sim.bio[g]["perfused"]
    sim.bio[g]["sprout_initial_neighbors"] = []  # fixture: connection acquired during extension
    sim.time = sim.p["sprout_duration_min"]
    sim.complete_programs()
    assert sim.bio[g]["perfusion_due"] == sim.time+sim.p["perfusion_delay_min"]
    assert not sim.segments[-1]["perfused"]
    sim.time += sim.p["perfusion_delay_min"]
    sim.advance_biology(10)
    assert sim.segments[-1]["perfused"] and sim.bio[g]["perfused"]


def test_recruitment_requires_perfusion_signal_and_preserves_accounting(sim):
    g,o = contact_action(sim,"DEGRANULATE")
    relabel(sim,g,"Endothelial")
    sim.scenario["recruitment"] = True
    sim.local_fields[g]["cxcl9"] = 1
    sim.bio[g]["perfused"] = False
    sim.recruit()
    assert sim.tissue.recruited == 0
    sim.bio[g]["perfused"] = True
    sim.recruit()
    assert sim.tissue.recruited == 1 and sim.tissue.origins[-1] == "recruited"
    sim.tissue.check_invariants()


def test_virtual_nerve_is_declared_and_never_queried(sim):
    c = copy.deepcopy(sim.contract)
    nerve = AutonomousSimulation(sim.atlas,c,"S5",4)
    assert len(nerve.nerve) == 2
    assert nerve.fields.values["ne"].max() > 0
    assert nerve.fields.values["cgrp"].max() == 0
    assert sim.fields.values["ne"].max() == 0
    assert len(nerve.tissue.ids) == len(sim.tissue.ids)
    assert nerve.fields.shape == sim.fields.shape
    assert np.array_equal(nerve.fields.origin,sim.fields.origin)
    assert np.array_equal(nerve.fields.values["oxygen"],sim.fields.values["oxygen"])
