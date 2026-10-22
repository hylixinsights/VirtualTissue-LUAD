from pathlib import Path
import pytest
from shapely.geometry import shape
from luad_tissue.io import read_json,fingerprint
from luad_tissue.engine import Simulation

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("region,expected",[(26,(2883,19,45,983)),(27,(2975,2,183,695))])
def test_reconstruction(region,expected):
    path=ROOT/f"outputs/atlas_B{region}.json.gz"
    if not path.exists():pytest.skip("Private atlas has not been built")
    atlas=read_json(path);claimed=atlas.pop("fingerprint");assert claimed==fingerprint(atlas)
    summary=atlas["summary"]
    assert (summary["internal_contact_pairs"],summary["cd8_tumor_pairs"],summary["caf_tumor_pairs"],summary["scored"])==expected
    by={c["cell_id"]:c for c in atlas["cells"]}
    for cell in atlas["cells"]:
        assert shape(cell["geometry"]).is_valid
        if cell["role"]!="roi":continue
        for edge in cell["contacts"]:
            assert edge["cell_id"] in by
            actual=shape(cell["geometry"]).distance(shape(by[edge["cell_id"]]["geometry"]))
            assert actual<=1.000001 and abs(actual-edge["gap_um"])<=.000501
            if by[edge["cell_id"]]["role"]=="roi":assert any(e["cell_id"]==cell["cell_id"] for e in by[edge["cell_id"]]["contacts"])
        assert len(cell["signatures"])==(20 if cell["qc"]["scored"] else 0)


def test_real_baseline_has_no_executable_cytotoxicity(rulebook,contract):
    path=ROOT/"outputs/atlas_B26.json.gz"
    if not path.exists():pytest.skip("Private atlas unavailable")
    sim=Simulation(read_json(path),rulebook,contract)
    assert sim.requests()==[]
    ambiguous=sim.by_id[95048]
    assert ambiguous["identity"]["candidates"][1]["label"]=="T_CD4"
