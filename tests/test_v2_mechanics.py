import copy
from pathlib import Path

import numpy as np
import pytest

from luad_tissue.io import fingerprint, read_json
from luad_tissue.v2.mechanics import InvariantError, Tissue
from luad_tissue.v2.runtime import SimulationV2
from v2_synthetic import synthetic_atlas

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def contract2():
    return read_json(ROOT / "contracts/runtime-v2.json")


@pytest.fixture
def atlas2():
    return synthetic_atlas()


def measured_pairs(atlas, tissue):
    pos = {int(c): g for g, c in enumerate(tissue.ids.tolist())}
    return {tuple(sorted((pos[c["cell_id"]], pos[e["cell_id"]]))) for c in atlas["cells"] if c["role"] == "roi"
            for e in c["contacts"] if e["gap_um"] <= 1}


def test_fit_reproduces_measured_areas_and_t0_is_an_equilibrium(atlas2, contract2):
    t = Tissue.from_atlas(atlas2, contract2)
    assert t.fit["hidden"] == 0
    assert t.fit["area_ratio_quantiles"][0] > .97 and t.fit["area_ratio_quantiles"][-1] < 1.03
    idx, g = t.geometry()
    assert t.pressure(idx, g).max() < 1e-9
    sim = SimulationV2(atlas2, contract2, "static").run(360)
    assert np.array_equal(sim.tissue.xy, sim.tissue.xy0)
    assert not sim.events and not sim.decisions


def test_contact_graph_is_the_measured_graph_at_t0(atlas2, contract2):
    t = Tissue.from_atlas(atlas2, contract2)
    idx, g = t.geometry()
    graph = t.contact_pairs(idx, g)
    acting = {p for p in graph if t.acts[p[0]] or t.acts[p[1]]}
    assert acting == measured_pairs(atlas2, t)
    assert all(graph[p] == "measured_contact_persisting" for p in acting)


def test_removal_frees_space_that_neighbours_take(atlas2, contract2):
    t = Tissue.from_atlas(atlas2, contract2)
    idx, g = t.geometry()
    centre = int(np.argmin(np.hypot(*(t.xy - t.centre).T)))
    neighbours = [b if a == centre else a for a, b in t.contact_pairs(idx, g) if centre in (a, b)]
    before = {k: g.area[list(idx).index(k)] for k in neighbours}
    t.remove(centre, "cleared")
    idx, g = t.geometry()
    after = {k: g.area[list(idx).index(k)] for k in neighbours}
    assert centre not in idx
    assert sum(after.values()) > sum(before.values())
    acc = t.check_invariants()
    assert acc["acting"]["cleared"] == 1
    with pytest.raises(InvariantError):
        t.remove(centre, "cleared")


def test_division_adds_one_daughter_and_keeps_accounting(atlas2, contract2):
    t = Tissue.from_atlas(atlas2, contract2)
    g0 = int(np.argmin(np.hypot(*(t.xy - t.centre).T)))
    t.A0[g0] *= 2
    daughter = t.divide(g0, [1., 0.], 30)
    assert t.origins[daughter] == "born" and t.parents[daughter] == int(t.ids[g0])
    assert t.A0[daughter] == pytest.approx(t.A0[g0])
    assert t.check_invariants()["expected_acting_total"] == t.n_initial_roi + 1
    assert t.overlap_audit()["overlap_um2"] <= 1e-6


def test_growth_divides_and_crowding_blocks(atlas2, contract2):
    free = SimulationV2(atlas2, contract2, "m1_exercise", seed=5).run(1500)
    kinds = {e["kind"] for e in free.events}
    assert "division" in kinds
    assert free.tissue.born == sum(e["kind"] == "division" for e in free.events)
    crowded = copy.deepcopy(contract2)
    crowded["division"]["division_blocked_local_pressure"] = -1.
    blocked = SimulationV2(atlas2, crowded, "m1_exercise", seed=5).run(1500)
    assert blocked.tissue.born == 0
    assert any(e["kind"] == "division_blocked_crowding" for e in blocked.events)


@pytest.mark.parametrize("mode", ["self_propelled", "swap"])
def test_motility_moves_cd8_keeps_boundary_fixed_and_confined(atlas2, contract2, mode):
    contract2["migration"]["mode"] = mode
    sim = SimulationV2(atlas2, contract2, "m1_exercise", seed=2).run(360)
    t = sim.tissue
    cd8 = [g for g in np.flatnonzero(t.acts) if t.labels[g] == "T_CD8_cytotoxic"]
    assert np.hypot(*(t.xy[cd8] - t.xy0[cd8]).T).max() > 5
    assert np.array_equal(t.xy[t.fixed], t.xy0[t.fixed])
    mobile = t.present & ~t.fixed
    assert (np.hypot(*(t.xy[mobile] - t.centre).T) <= t.fixed_radius + 1e-9).all()
    assert t.overlap_audit()["relative_overlap"] < 1e-9
    assert all(d["answer"]["choice"] in d["options"] for d in sim.decisions)


def test_seeded_reproducibility_and_episode_fingerprint(atlas2, contract2):
    first = SimulationV2(atlas2, contract2, "m1_exercise", seed=9).run(240).episode()
    second = SimulationV2(atlas2, contract2, "m1_exercise", seed=9).run(240).episode()
    other = SimulationV2(atlas2, contract2, "m1_exercise", seed=10).run(240).episode()
    assert first["fingerprint"] == second["fingerprint"] != other["fingerprint"]
    claimed = first.pop("fingerprint")
    assert fingerprint(first) == claimed
    assert first["paid_calls"] == 0 and first["t0"]["display"] == "measured polygons"


def test_accounting_corruption_is_detected(atlas2, contract2):
    t = Tissue.from_atlas(atlas2, contract2)
    t.born += 1
    with pytest.raises(InvariantError):
        t.check_invariants()
    t = Tissue.from_atlas(atlas2, contract2)
    t.xy[np.flatnonzero(t.fixed)[0]] += 1
    with pytest.raises(InvariantError):
        t.check_invariants()


def test_policy_may_only_choose_offered_options(atlas2, contract2):
    class Rogue:
        name = "rogue_fixture"

        def choose(self, requests):
            return {r["cell_id"]: dict(choice="divide_now", probabilities={}, confidence=1.) for r in requests}

    with pytest.raises(ValueError):
        SimulationV2(atlas2, contract2, "m1_exercise", policy=Rogue()).step()


def test_v2_leaves_v1_runtime_untouched():
    import luad_tissue.engine as engine
    v1 = read_json(ROOT / "contracts/runtime-v1.json")
    assert v1["version"] == "luad-runtime-0.1.0"
    assert "v2" not in open(engine.__file__, encoding="utf-8").read()
