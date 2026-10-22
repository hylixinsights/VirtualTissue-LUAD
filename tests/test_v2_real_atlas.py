from pathlib import Path

import numpy as np
import pytest

from luad_tissue.io import read_json
from luad_tissue.v2.runtime import SimulationV2

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def b26():
    path = ROOT / "outputs/atlas_B26.json.gz"
    if not path.exists():
        pytest.skip("Private atlas has not been built")
    return read_json(path), read_json(ROOT / "contracts/runtime-v2.json")


def test_b26_t0_fidelity(b26):
    atlas, contract = b26
    sim = SimulationV2(atlas, contract, "static")
    fit = sim.fidelity["fitted"]
    assert sim.tissue.fit["hidden"] == 0
    assert fit["iou_by_type"]["all_roi"]["median"] >= .75
    assert fit["contacts_any_roi"]["f1"] >= .88
    assert fit["contacts_any_roi"]["f1"] > sim.fidelity["unfitted"]["contacts_any_roi"]["f1"]
    idx, g = sim.tissue.geometry()
    graph = sim.tissue.contact_pairs(idx, g)
    labels = sim.tissue.labels
    cd8_tumour = [p for p in graph if {labels[p[0]], labels[p[1]]} >= {"T_CD8_cytotoxic"}
                  and {labels[p[0]], labels[p[1]]} & {"Tumor", "Tumor_proliferating"}]
    assert len(cd8_tumour) == atlas["summary"]["cd8_tumor_pairs"] == 19


def test_b26_short_exercise_run_keeps_invariants(b26):
    atlas, contract = b26
    sim = SimulationV2(atlas, contract, "m1_exercise", seed=21).run(120)
    t = sim.tissue
    assert np.array_equal(t.xy[t.fixed], t.xy0[t.fixed])
    assert t.overlap_audit()["relative_overlap"] < 1e-9
    assert sim.metrics[-1]["hidden"] <= 2
