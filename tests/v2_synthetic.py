"""Synthetic packed tissue for v2 tests: jittered square cells with 0.5 um gaps."""
import numpy as np
from shapely.geometry import box, mapping

from luad_tissue.io import fingerprint

LINEAGE = {"T_CD8_cytotoxic": "T", "Tumor_proliferating": "tumor", "Tumor": "tumor", "B_cell": "B_lineage",
           "Fibroblast": "stromal", "Endothelial": "endothelial"}


def synthetic_atlas(n=13, pitch=8.5, side=8.0, roi_radius=26., halo_um=30., seed=3):
    rng = np.random.default_rng(seed)
    centre = np.array([(n - 1) * pitch / 2] * 2)
    cells = []
    for r in range(n):
        for c in range(n):
            cid = r * n + c + 1
            x, y = c * pitch + rng.uniform(-.2, .2), r * pitch + rng.uniform(-.2, .2)
            d = float(np.hypot(x - centre[0], y - centre[1]))
            if d < 9:
                label = "Tumor_proliferating"
            elif d < 22:
                label = "T_CD8_cytotoxic" if cid % 2 else "B_cell"
            elif (r + c) % 5 == 0:
                label = "Endothelial"
            elif (r + c) % 3 == 0:
                label = "Fibroblast"
            else:
                label = "B_cell"
            polygon = box(x - side / 2, y - side / 2, x + side / 2, y + side / 2)
            cells.append(dict(cell_id=cid, role="roi" if d <= roi_radius else "halo", geometry=mapping(polygon),
                              area_um2=polygon.area, x=x, y=y, polygon_repaired=False,
                              identity=dict(candidates=[dict(label=label, source="cell_type_fine", lineage=LINEAGE[label]),
                                                        dict(label=label, source="first_type", lineage=LINEAGE[label])],
                                            agreement="concordant_exact"),
                              genes_detected=[], panel_genes=[], signatures={}, region={}, qc=dict(scored=False), contacts=[],
                              neighbour_ids_30um=[], _poly=polygon))
    for a in cells:
        if a["role"] != "roi":
            continue
        for b in cells:
            if b is a:
                continue
            gap = a["_poly"].distance(b["_poly"])
            if gap <= 1:
                a["contacts"].append(dict(cell_id=b["cell_id"], gap_um=round(gap, 3), interface_um=side,
                                          outside_patch=b["role"] != "roi", occluded=False))
    for cell in cells:
        del cell["_poly"]
    data = dict(schema_version="1.0.0", patch_id="SYNTHETIC_V2", summary=dict(n_roi=sum(c["role"] == "roi" for c in cells)),
                geometry=dict(center_um=centre.tolist(), halo_um=halo_um, radius_um=roi_radius), cells=cells)
    return {**data, "fingerprint": fingerprint(data)}
