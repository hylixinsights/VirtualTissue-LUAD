"""Reconstruct a measured patch, its full polygons, and a frozen spatial halo."""
from collections import Counter
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
from scipy.sparse import csc_matrix, csr_matrix
from scipy.spatial import cKDTree
from shapely import Polygon, STRtree, buffer, intersection, union_all
from shapely.geometry import mapping

from .conditions import eligibility_summary
from .io import file_hash, fingerprint, read_json, write_json


def categorical(obs, name):
    group = obs[name]
    categories = group["categories"].asstr()[:]
    codes = group["codes"][:]
    return np.array([categories[i] if i >= 0 else "unknown" for i in codes])


def polygons_from_csv(path):
    table = pd.read_csv(path)
    coords = table[["vertex_x", "vertex_y"]].to_numpy()
    ids = table["cell_id"].to_numpy()
    starts = np.flatnonzero(np.r_[True, ids[1:] != ids[:-1]])
    ends = np.r_[starts[1:], len(ids)]
    shapes, repaired = {}, []
    for start, end in zip(starts, ends):
        cid = int(ids[start])
        if cid in shapes:
            raise ValueError(f"Non-contiguous or duplicate polygon ID {cid}")
        polygon = Polygon(coords[start:end])
        if not polygon.is_valid:
            polygon = polygon.buffer(0)
            repaired.append(cid)
        if polygon.is_empty or polygon.geom_type not in ("Polygon", "MultiPolygon"):
            raise ValueError(f"Invalid or empty polygon {cid}")
        shapes[cid] = polygon
    return shapes, repaired


def build_atlas(root, raw_dir, candidate=26, n_cells=1000, halo_um=30):
    root, raw_dir = Path(root), Path(raw_dir)
    rb = read_json(root / "rulebook/rulebook.json")
    cal = read_json(root / "rulebook/calibration.json")
    contract = read_json(root / "contracts/runtime-v1.json")
    h5path, bounds = raw_dir / "LUAD3_TLS_GO20_UCell.h5ad", raw_dir / "cell_boundaries.csv"
    h5hash = file_hash(h5path)
    if h5hash != rb["sample"]["delivered_sha256"] or h5hash != cal["source"]["sha256"]:
        raise ValueError("Source H5AD fingerprint differs from the frozen rulebook/calibration")
    if file_hash(root / "rulebook/rulebook.json") != contract["reference_rulebook_sha256"]:
        raise ValueError("Reference rulebook changed without a runtime-contract revision")
    if n_cells < 1 or halo_um < 30 or not np.isfinite(halo_um):
        raise ValueError("Use a positive cell count and a finite halo of at least 30 um")
    shapes, repaired = polygons_from_csv(bounds)
    shape_ids = np.array(list(shapes))
    shape_list = list(shapes.values())
    tree = STRtree(shape_list)
    with h5py.File(h5path, "r") as f:
        obs = f["obs"]
        ids, xy = obs["cell_id"][:], f["obsm/spatial"][:]
        if n_cells > len(ids) or len(set(map(int, ids))) != len(ids):
            raise ValueError("Invalid requested size or duplicate annotated identifiers")
        rows = {int(cid): i for i, cid in enumerate(ids)}
        gid, core = obs["geodesic_candidate_id"][:], obs["is_candidate_core"][:]
        mask = (gid == candidate) & (core == 1)
        if not mask.any():
            raise ValueError(f"Candidate B{candidate} has no core")
        center = xy[mask].mean(axis=0)
        distances, selected = cKDTree(xy).query(center, k=n_cells)
        selected = np.atleast_1d(selected)
        roi_ids = set(map(int, ids[selected]))
        missing = roi_ids - shapes.keys()
        if missing:
            raise ValueError(f"Missing ROI polygons: {sorted(missing)}")
        roi_union = union_all([shapes[cid] for cid in roi_ids])
        envelope = buffer(roi_union, halo_um)
        kept = {int(shape_ids[i]) for i in tree.query(envelope, predicate="intersects")}
        contacts = {}
        for cid in sorted(roi_ids):
            polygon = shapes[cid]
            edges = []
            for index in tree.query(buffer(polygon, 1.5)):
                other_id, other = int(shape_ids[index]), shape_list[index]
                if cid == other_id:
                    continue
                gap = float(polygon.distance(other))
                if gap > 1:
                    continue
                iface = intersection(buffer(polygon, .75, quad_segs=2), buffer(other, .75, quad_segs=2)).area / 1.5
                edges.append(dict(cell_id=other_id, gap_um=round(gap, 3), interface_um=round(float(iface), 2),
                                  outside_patch=other_id not in roi_ids and other_id in rows, occluded=other_id not in rows))
                kept.add(other_id)
            contacts[cid] = sorted(edges, key=lambda e: (-e["interface_um"], e["cell_id"]))
        primary, secondary = categorical(obs, "cell_type_fine"), categorical(obs, "first_type")
        stage, tls_class = categorical(obs, "TLS_stage_name"), categorical(obs, "TLS_class")
        panel = list(f["var/_index"].asstr()[:])
        layer = f["layers/purified_raw"]
        encoding = layer.attrs["encoding-type"]
        matrix_class = {"csc_matrix": csc_matrix, "csr_matrix": csr_matrix}.get(encoding)
        if matrix_class is None:
            raise ValueError(f"Unsupported expression encoding {encoding}")
        expr = matrix_class((layer["data"][:], layer["indices"][:], layer["indptr"][:]), shape=tuple(layer.attrs["shape"])).tocsr()
        expr.eliminate_zeros()
        neighbours = cKDTree(xy)
        raw_arrays = {name: obs[meta["obs_column"]][:] for name, meta in cal["signatures"].items()}
        scalar_names = ["go20_scored", "n_genes_by_counts", "transcript_counts", "is_tumor_core", "TLS_stage", "dist_to_nearest_tumor_core", "dist_to_nearest_core"]
        scalars = {name: obs[name][:] for name in scalar_names}
        cells = []
        for cid in sorted(kept):
            polygon = shapes[cid]
            cell = dict(cell_id=cid, role="roi" if cid in roi_ids else "halo" if cid in rows else "occluded",
                        geometry=mapping(polygon), area_um2=float(polygon.area), contacts=contacts.get(cid, []),
                        x=float(polygon.centroid.x), y=float(polygon.centroid.y), polygon_repaired=cid in repaired)
            if cid not in rows:
                cell.update(identity=None, genes_detected=[], panel_genes=[], signatures={}, region={}, qc={}, neighbour_ids_30um=[])
                cells.append(cell)
                continue
            i = rows[cid]
            a, b = str(primary[i]), str(secondary[i])
            la = rb["annotation"]["lineage_map"]["cell_type_fine"].get(a)
            lb = rb["annotation"]["lineage_map"]["first_type"].get(b)
            agreement = "concordant_exact" if a == b else "concordant_lineage" if la is not None and la == lb else "conflict"
            cell.update(x=float(xy[i, 0]), y=float(xy[i, 1]),
                        identity=dict(candidates=[dict(label=a, source="cell_type_fine", lineage=la), dict(label=b, source="first_type", lineage=lb)], agreement=agreement),
                        genes_detected=sorted(panel[j] for j, v in zip(expr.getrow(i).indices, expr.getrow(i).data) if v > 0),
                        panel_genes=panel,
                        region=dict(geodesic_candidate_id=int(gid[i]), is_candidate_core=int(core[i]), is_tumor_core=bool(scalars["is_tumor_core"][i]),
                                    tls_stage_name=str(stage[i]), tls_stage_int=int(scalars["TLS_stage"][i]), tls_class=str(tls_class[i]),
                                    tls_maturity_evidence="delivered_label_uncorroborated", dist_to_nearest_tumor_core_um=float(scalars["dist_to_nearest_tumor_core"][i])),
                        qc=dict(scored=bool(scalars["go20_scored"][i]), n_genes_by_counts=int(scalars["n_genes_by_counts"][i]), transcript_counts=int(scalars["transcript_counts"][i])),
                        neighbour_ids_30um=[int(ids[j]) for j in neighbours.query_ball_point(xy[i], 30) if j != i and int(ids[j]) in kept], signatures={})
            ct = cal["cell_types"].get(a)
            if cell["qc"]["scored"] and ct:
                decile = int(np.clip(np.searchsorted(ct["depth_decile_edges"][1:-1], cell["qc"]["n_genes_by_counts"], side="right"), 0, 9))
                cell["qc"]["depth_decile_within_type"] = decile
                for name, reference in ct["signatures"].items():
                    raw = float(raw_arrays[name][i])
                    median = reference["median_by_depth_decile"][decile]
                    if not np.isfinite(raw):
                        raise ValueError(f"Nonfinite score in scored cell {cid}")
                    cell["signatures"][name] = dict(raw=raw, depth_residual=raw - median if median is not None else None,
                         percentile_within_type=0. if raw <= reference["percentile_edges"][0] else 1. if raw >= reference["percentile_edges"][-1] else float(np.interp(raw, reference["percentile_edges"], reference["percentile_grid"])) / 100,
                         coverage_flag="identity_confounded" if reference["coverage_flag"] == "identity_confounded" else "low_coverage",
                         reference_coverage_flag=reference["coverage_flag"])
            cells.append(cell)
    pairs = {tuple(sorted((cid, e["cell_id"]))) for cid, edges in contacts.items() for e in edges if e["cell_id"] in roi_ids}
    by_id = {c["cell_id"]: c for c in cells}
    labels = {cid: by_id[cid]["identity"]["candidates"][0]["label"] for cid in roi_ids}
    tumor = {"Tumor", "Tumor_proliferating"}
    def pair_count(kind):
        return sum((labels[a] == kind and labels[b] in tumor) or (labels[b] == kind and labels[a] in tumor) for a, b in pairs)
    roi = [c for c in cells if c["role"] == "roi"]
    summary = dict(n_roi=len(roi), n_context=len(cells) - len(roi), roles=dict(Counter(c["role"] for c in cells)),
        composition=dict(Counter(labels.values())), identity=dict(Counter(c["identity"]["agreement"] for c in roi)),
        scored=sum(c["qc"]["scored"] for c in roi), internal_contact_pairs=len(pairs), cd8_tumor_pairs=pair_count("T_CD8_cytotoxic"), caf_tumor_pairs=pair_count("CAF"),
        contact_edges_to_halo=sum(e["outside_patch"] for c in roi for e in c["contacts"]),
        contact_edges_to_occluded=sum(e["occluded"] for c in roi for e in c["contacts"]),
        contacted_occluded=len({e["cell_id"] for c in roi for e in c["contacts"] if e["occluded"]}),
        contacted_halo=len({e["cell_id"] for c in roi for e in c["contacts"] if e["outside_patch"]}),
        mean_degree=sum(len(c["contacts"]) for c in roi) / len(roi))
    atlas = dict(schema_version="1.0.0", patch_id=f"LUAD3_B{candidate}", summary=summary,
        geometry=dict(center_um=list(map(float, center)), radius_um=float(np.max(distances)), roi_bounds_um=list(roi_union.bounds), halo_um=halo_um,
                      coordinate_source="obsm/spatial in micrometres; original Xenium orientation", dimension=2),
        provenance=dict(source_h5ad_sha256=h5hash, boundaries_sha256=file_hash(bounds), calibration_sha256=file_hash(root / "rulebook/calibration.json"),
                        rulebook_sha256=file_hash(root / "rulebook/rulebook.json"), runtime_contract_sha256=fingerprint(contract),
                        expression_layer="purified_raw", polygon_repairs_in_domain=[cid for cid in repaired if cid in kept],
                        contact_definition="polygon distance <= 1 um", interface_estimator="buffer overlap area / 1.5 um; approximate interface length",
                        boundary_policy=contract["boundary_policy"]),
        signatures=cal["signatures"], cells=cells)
    reference = root / "examples/patch_B26.json"
    if candidate == 26 and n_cells == 1000 and reference.exists():
        frozen = read_json(reference)
        if roi_ids != {c["cell_id"] for c in frozen["cells"]}:
            raise ValueError("B26 ROI differs from frozen reference")
        ref_pairs = {tuple(sorted((c["cell_id"], e["cell_id"]))) for c in frozen["cells"] for e in c["contacts"] if e["cell_id"] in roi_ids}
        if pairs != ref_pairs:
            raise ValueError("Reconstructed B26 contact graph differs from reference")
        atlas["provenance"]["reference_patch_sha256"] = file_hash(reference)
        atlas["provenance"]["reference_roi_and_graph_match"] = True
    atlas["baseline_eligibility"] = eligibility_summary(atlas, rb["rules"], contract)
    atlas["fingerprint"] = fingerprint(atlas)
    return atlas
