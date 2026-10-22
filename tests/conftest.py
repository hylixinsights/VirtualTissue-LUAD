import copy
import os
from pathlib import Path
import pytest
from luad_tissue.io import read_json, fingerprint

ROOT = Path(__file__).resolve().parents[1]
TEMP_ROOT = ROOT / ".cache" / "test-tmp"
TEMP_ROOT.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("PYTEST_DEBUG_TEMPROOT", str(TEMP_ROOT))


@pytest.fixture
def contract():
    return read_json(ROOT / "contracts/runtime-v1.json")


@pytest.fixture
def rulebook():
    return read_json(ROOT / "rulebook/rulebook.json")


def make_cell(cid, label, secondary=None):
    lineage = {"T_CD8_cytotoxic": "T", "T_CD4": "T", "Tumor": "tumor", "Macrophage_SPP1": "myeloid", "Plasma_cell": "B_lineage"}[label]
    secondary = secondary or label
    return dict(cell_id=cid, x=(cid-1)*4., y=0., role="roi", area_um2=16.,
        identity=dict(candidates=[dict(label=label, source="cell_type_fine", lineage=lineage), dict(label=secondary, source="first_type", lineage=lineage)],
                      agreement="concordant_exact" if secondary == label else "concordant_lineage"),
        genes_detected=["CD8A", "PRF1", "MZB1"], panel_genes=["CD8A", "PRF1", "MZB1", "XBP1"],
        contacts=[], neighbour_ids_30um=[], signatures={}, qc=dict(scored=False,n_genes_by_counts=3), region={},
        geometry=dict(type="Polygon",coordinates=[[[ (cid-1)*4-2,-2],[(cid-1)*4+2,-2],[(cid-1)*4+2,2],[(cid-1)*4-2,2],[(cid-1)*4-2,-2]]]))


@pytest.fixture
def atlas():
    cells = [make_cell(1,"T_CD8_cytotoxic"),make_cell(2,"Tumor"),make_cell(3,"Macrophage_SPP1")]
    for a,b in [(1,2),(2,1),(2,3),(3,2)]:
        cells[a-1]["contacts"].append(dict(cell_id=b,gap_um=0.,interface_um=4.))
    data = dict(schema_version="1.0.0", patch_id="SYNTHETIC",summary=dict(n_roi=3),cells=cells)
    return {**data,"fingerprint":fingerprint(data)}
