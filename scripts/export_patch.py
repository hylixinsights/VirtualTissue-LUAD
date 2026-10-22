#!/usr/bin/env python3
"""Cut a simulation patch out of the LUAD3 section and write it as JSON.

Reads LUAD3_TLS_GO20_UCell.h5ad and cell_boundaries.csv. Writes one patch file
containing every cell the engine needs to instantiate, its measured state, its
true contact graph, and the segmented-but-unannotated cells that occupy space
inside the window.

The default patch (--candidate 26) is the reference patch documented in
MANUAL.md section 11: a primary-follicle TLS core abutting a proliferating
tumour nest, 1,000 cells in a 324 x 321 um window. It is the only window in the
section that contains both a lymphoid follicle and a tumour nest with a
non-trivial number of CD8-tumour contacts.

Usage
-----
    python scripts/export_patch.py \
        --h5ad LUAD3_TLS_GO20_UCell.h5ad \
        --boundaries cell_boundaries.csv \
        --calibration rulebook/calibration.json \
        --candidate 26 --n-cells 1000 \
        --out examples/patch_B26.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from shapely import Polygon, STRtree, buffer, distance, intersection

CONTACT_GAP_UM = 1.0
INTERFACE_EPS_UM = 0.75
NEIGHBOURHOOD_UM = 30.0

# Marker genes the rulebook actually references. Exporting all 302 would triple
# the file for no gain; this list is the union of every gene named in a rule,
# capability or interaction edge in rulebook.json.
RULEBOOK_GENES = [
    "PTPRC", "CD3E", "CD4", "CD8A", "LCK", "LAT", "TRAT1", "GZMA", "GZMB", "PRF1",
    "PDCD1", "LAG3", "TIGIT", "CTLA4", "FOXP3", "IL2RA", "ICOS", "TBX21",
    "CXCR5", "CXCR6", "CD40LG", "SELL", "CCR7", "ITGAE",
    "CD19", "BANK1", "TCL1A", "FCMR", "POU2AF1", "SPIB", "RGS13",
    "MZB1", "TNFRSF17", "TNFRSF13B", "XBP1", "PRDX4", "DNAJB9",
    "CD68", "CD163", "MSR1", "MARCO", "TREM2", "SPP1", "C1QC", "ITGAM", "ITGAX",
    "LILRB2", "LAMP3", "FSCN1", "CD1C", "CLEC10A", "CLEC4C",
    "CCL22", "CCL13", "IL1B", "TNF", "IL6", "CXCL9", "CXCL13", "CCL21", "CXCL14",
    "HLA-A", "HLA-DPB1", "CD74", "CD80", "CD86", "CD274", "IDO1", "ICAM1",
    "NECTIN2", "PVR", "CD44",
    "KRT8", "CDH1", "NAPSA", "SFTPB", "EGFR", "MET", "ERBB2", "AXL", "YAP1",
    "ZEB1", "VIM", "MKI67", "UBE2C", "ASPM", "TP53", "VEGFA", "SLC2A1", "ATF4",
    "HYOU1", "CAV1", "TGFB1",
    "COL1A1", "PDGFRA", "FAP", "POSTN", "ACTA2", "TNC", "MMP7", "MMP9", "MMP11",
    "CTSK", "PDPN", "FDCSP",
    "PECAM1", "KDR", "PLVAP", "PROX1", "LYVE1", "MMRN1", "SELP", "RGS5",
]

# Genes that SPLIT removes almost entirely from purified_raw, the layer both the
# UCell scores and this export read. 292 of 302 genes are unaffected. Three of the
# seven are MHC genes, which is why the antigen-presentation axis is weak here.
# Mirrors rulebook.panel.layer_sensitive_genes.
LAYER_SENSITIVE = {
    "HLA-A": 0.6279, "HLA-DPB1": 0.5732, "PTP4A1": 0.4785, "HLA-DQB2": 0.1729,
    "AKR1C1": 0.1403, "KRT81": 0.0908, "DAPL1": 0.0594,
}

# Coarse lineage, for telling a vocabulary difference apart from a real disagreement.
# Mirrors rulebook.annotation.lineage_map.
LINEAGE = {
    "cell_type_fine": {"B_cell": "B_lineage", "Plasma_cell": "B_lineage", "T_CD4": "T",
                       "T_CD8_cytotoxic": "T", "Macrophage_SPP1": "myeloid", "CAF": "stromal",
                       "Fibroblast": "stromal", "Endothelial": "endothelial",
                       "Tumor": "tumor", "Tumor_proliferating": "tumor"},
    "first_type": {"B_cell": "B_lineage", "T_CD4": "T", "T_CD8": "T", "DC": "myeloid",
                   "Myeloid": "myeloid", "Stromal": "stromal", "Endothelial": "endothelial",
                   "Tumor": "tumor", "Mast_NK": "other", "Undefined": "other"},
}

# (gene, cell type) pairs whose detection in LUAD3 is inconsistent with the
# canonical source of that transcript. Flagged per observation so a rule can
# refuse to treat them as evidence. See MANUAL.md section 9.2.
SPILLOVER_PRIORS = {
    "SFTPB": "high_alveolar_ambient",
    "NAPSA": "high_alveolar_ambient",
    "KRT8": "high_epithelial_ambient",
    "CDH1": "high_epithelial_ambient",
    "MET": "high_epithelial_ambient",
    "EGFR": "high_epithelial_ambient",
    "COL1A1": "high_stromal_ambient",
    "ACTA2": "high_stromal_ambient",
    "CXCL13": "anomalous_in_B_cell_verify",
    "FDCSP": "anomalous_in_B_cell_verify",
    "PRF1": "anomalous_in_Tumor_verify",
    "LAMP3": "not_DC_specific_in_this_section",
}


def categorical(obs, name):
    grp = obs[name]
    cats = np.array([c.decode() if isinstance(c, bytes) else c for c in grp["categories"][:]])
    codes = grp["codes"][:]
    return np.where(codes >= 0, cats[np.clip(codes, 0, None)], "NA")


def decode(arr):
    return [v.decode() if isinstance(v, bytes) else v for v in arr[:]]


def percentile_of(value, edges, grid):
    """Linear interpolation of value against the stored percentile edges."""
    if value <= edges[0]:
        return float(grid[0]) / 100.0
    if value >= edges[-1]:
        return float(grid[-1]) / 100.0
    k = int(np.searchsorted(edges, value, side="right")) - 1
    k = max(0, min(k, len(edges) - 2))
    span = edges[k + 1] - edges[k]
    frac = 0.0 if span <= 0 else (value - edges[k]) / span
    return (grid[k] + frac * (grid[k + 1] - grid[k])) / 100.0


def build_polygons(boundaries_csv: Path):
    b = pd.read_csv(boundaries_csv)
    arr = b[["vertex_x", "vertex_y"]].to_numpy()
    ids = b["cell_id"].to_numpy()
    starts = np.flatnonzero(np.r_[True, ids[1:] != ids[:-1]])
    ends = np.r_[starts[1:], len(ids)]
    uid, polys = [], []
    for s, e in zip(starts, ends):
        if e - s < 3:
            continue
        p = Polygon(arr[s:e])
        if not p.is_valid:
            p = p.buffer(0)
        if p.is_empty:
            continue
        uid.append(int(ids[s]))
        polys.append(p)
    return np.array(uid), np.array(polys, dtype=object)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--h5ad", required=True, type=Path)
    ap.add_argument("--boundaries", required=True, type=Path)
    ap.add_argument("--calibration", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--candidate", type=int, default=26,
                    help="geodesic_candidate_id whose core centroid centres the window")
    ap.add_argument("--centre", type=float, nargs=2, default=None,
                    help="explicit window centre in um, overrides --candidate")
    ap.add_argument("--n-cells", type=int, default=1000)
    ap.add_argument("--patch-id", default=None)
    args = ap.parse_args()

    calib = json.loads(args.calibration.read_text(encoding="utf-8"))
    annotation = calib["source"]["annotation_column"]

    f = h5py.File(args.h5ad, "r")
    obs = f["obs"]
    xy = f["obsm"]["spatial"][:]
    cell_id = obs["cell_id"][:]
    primary = categorical(obs, annotation)
    secondary = categorical(obs, "first_type" if annotation != "first_type" else "cell_type_fine")
    gid = obs["geodesic_candidate_id"][:]
    core = obs["is_candidate_core"][:]
    scored = obs["go20_scored"][:]
    stage = categorical(obs, "TLS_stage_name")
    tls_class = categorical(obs, "TLS_class")
    stage_int = obs["TLS_stage"][:]
    d2tumor = obs["dist_to_nearest_tumor_core"][:]
    d2core = obs["dist_to_nearest_core"][:]
    is_tumor_core = obs["is_tumor_core"][:]
    n_genes = obs["n_genes_by_counts"][:]
    transcripts = obs["transcript_counts"][:]

    genes = np.array(decode(f["var"]["_index"]))
    gene_index = {g: i for i, g in enumerate(genes)}
    layer = f["layers"]["purified_raw"]          # CSC: indptr indexes genes
    indptr, indices = layer["indptr"][:], layer["indices"][:]

    present = [g for g in RULEBOOK_GENES if g in gene_index]
    detected = {}
    for g in present:
        j = gene_index[g]
        rows = indices[indptr[j]:indptr[j + 1]]
        mask = np.zeros(len(cell_id), dtype=bool)
        mask[rows] = True
        detected[g] = mask

    if args.centre is not None:
        cx, cy = args.centre
        patch_id = args.patch_id or f"LUAD3_{int(cx)}_{int(cy)}"
    else:
        m = (gid == args.candidate) & (core == 1)
        if not m.any():
            raise SystemExit(f"candidate {args.candidate} has no core cells")
        cx, cy = float(xy[m, 0].mean()), float(xy[m, 1].mean())
        patch_id = args.patch_id or f"LUAD3_B{args.candidate}"

    tree = cKDTree(xy)
    dist, sel = tree.query([cx, cy], k=args.n_cells)
    radius = float(dist.max())
    sel = np.asarray(sel)
    in_patch = set(int(c) for c in cell_id[sel])

    uid, polys = build_polygons(args.boundaries)
    annotated = set(int(c) for c in cell_id)
    pos_by_uid = {int(u): i for i, u in enumerate(uid)}

    # Contacts are computed against ALL segmented cells, then split into
    # annotated partners and occluded (QC-dropped) ones.
    patch_poly_idx = [pos_by_uid[c] for c in in_patch if c in pos_by_uid]
    window = [p for p in polys[patch_poly_idx]]
    window_uid = [uid[i] for i in patch_poly_idx]
    tree_all = STRtree(polys)
    contacts = {c: [] for c in in_patch}
    occluded = {}
    for u, poly in zip(window_uid, window):
        for k in tree_all.query(buffer(poly, CONTACT_GAP_UM + 0.5)):
            other = int(uid[k])
            if other == int(u):
                continue
            gap = float(distance(poly, polys[k]))
            if gap > CONTACT_GAP_UM:
                continue
            iface = float(
                intersection(
                    buffer(poly, INTERFACE_EPS_UM, quad_segs=2),
                    buffer(polys[k], INTERFACE_EPS_UM, quad_segs=2),
                ).area
            ) / (2 * INTERFACE_EPS_UM)
            entry = {"cell_id": other, "gap_um": round(gap, 3), "interface_um": round(iface, 2)}
            if other not in annotated:
                entry["occluded"] = True
                if other not in occluded:
                    occluded[other] = {
                        "cell_id": other,
                        "x": round(float(polys[k].centroid.x), 2),
                        "y": round(float(polys[k].centroid.y), 2),
                        "area_um2": round(float(polys[k].area), 1),
                        "role": "occupies_space_no_identity_no_repertoire",
                    }
            elif other not in in_patch:
                entry["outside_patch"] = True
            contacts[int(u)].append(entry)

    sig_cols = {gs: meta["obs_column"] for gs, meta in calib["signatures"].items()}
    sig_values = {gs: obs[col][:] for gs, col in sig_cols.items()}

    nb_tree = cKDTree(xy)
    row_of = {int(c): i for i, c in enumerate(cell_id)}

    cells = []
    for i in sel:
        cid = int(cell_id[i])
        lab_p, lab_s = str(primary[i]), str(secondary[i])
        secondary_col = "first_type" if annotation != "first_type" else "cell_type_fine"
        lin_p = LINEAGE.get(annotation, {}).get(lab_p)
        lin_s = LINEAGE.get(secondary_col, {}).get(lab_s)
        if lab_p == lab_s:
            agreement = "concordant_exact"
        elif lin_p is not None and lin_p == lin_s:
            agreement = "concordant_lineage"
        else:
            agreement = "conflict"
        ct = calib["cell_types"].get(lab_p)

        sigs = {}
        if scored[i] and ct is not None:
            d_edges = ct["depth_decile_edges"]
            decile = int(np.clip(np.searchsorted(d_edges[1:-1], n_genes[i], side="right"), 0, 9))
            for gs, ref in ct["signatures"].items():
                raw = float(sig_values[gs][i])
                med = ref["median_by_depth_decile"][decile]
                sigs[gs] = {
                    "raw": round(raw, 5),
                    "percentile_within_type": round(
                        percentile_of(raw, ref["percentile_edges"], ref["percentile_grid"]), 4),
                    "depth_residual": None if med is None else round(raw - med, 5),
                    "coverage_flag": ref["coverage_flag"],
                }
        else:
            decile = None

        det = sorted(g for g in present if detected[g][i])
        nb = [j for j in nb_tree.query_ball_point(xy[i], NEIGHBOURHOOD_UM) if j != i]
        nb_counts = pd.Series(primary[nb]).value_counts().to_dict() if nb else {}

        cells.append({
            "cell_id": cid,
            "x": round(float(xy[i, 0]), 3),
            "y": round(float(xy[i, 1]), 3),
            "identity": {
                "candidates": [
                    {"label": lab_p, "source": annotation, "lineage": lin_p},
                    {"label": lab_s, "source": secondary_col, "lineage": lin_s},
                ],
                "agreement": agreement,
                "lineage": lin_p if agreement != "conflict" else None,
                "canonical_type": lab_p if agreement == "concordant_exact" else None,
                "ontogeny": "unknown",
            },
            "region": {
                "geodesic_candidate_id": int(gid[i]),
                "is_candidate_core": int(core[i]),
                "tls_class": str(tls_class[i]),
                "tls_stage_name": str(stage[i]),
                "tls_stage_int": int(stage_int[i]),
                "tls_maturity_evidence": "delivered_label_uncorroborated",
                "is_tumor_core": bool(is_tumor_core[i]),
                "dist_to_nearest_tumor_core_um": round(float(d2tumor[i]), 2),
                "dist_to_nearest_lymphoid_core_um": round(float(d2core[i]), 2),
            },
            "qc": {
                "n_genes_by_counts": int(n_genes[i]),
                "transcript_counts": int(transcripts[i]),
                "depth_decile_within_type": decile,
                "scored": bool(scored[i]),
            },
            "signatures": sigs,
            "genes_detected": det,
            "gene_flags": {
                **{g: SPILLOVER_PRIORS[g] for g in det if g in SPILLOVER_PRIORS},
                **{g: f"layer_sensitive: {LAYER_SENSITIVE[g]:.1%} in raw_counts, near zero here"
                   for g in present if g in LAYER_SENSITIVE},
            },
            "contacts": sorted(contacts[cid], key=lambda e: -e["interface_um"]),
            "neighbourhood_30um": {
                "n": len(nb),
                "by_type": {str(k): int(v) for k, v in nb_counts.items()},
                "admissible_use": "soluble_mediator_exposure_only",
            },
            "latent": {
                "viability_state": "assumed_alive",
                "cognate_target_recognition": "unobservable_by_design",
                "oxygen": None,
                "damage": {},
            },
        })

    comp = pd.Series([c["identity"]["candidates"][0]["label"] for c in cells]).value_counts()
    doc = {
        "patch_schema_version": "1.0.0",
        "patch_id": patch_id,
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "provenance": {
            "h5ad": args.h5ad.name,
            "boundaries": args.boundaries.name,
            "calibration_version": calib["calibration_version"],
            "annotation_column": annotation,
            "contact_definition": f"polygon boundary gap <= {CONTACT_GAP_UM} um",
            "gene_evidence_layer": "purified_raw",
            "gene_evidence_layer_note": "the layer UCell ranked; seven genes (HLA-A, HLA-DPB1, "
                                        "PTP4A1, HLA-DQB2, AKR1C1, KRT81, DAPL1) are present in "
                                        "raw_counts and effectively absent here",
            "interface_estimator": f"area(A+eps ^ B+eps)/(2*eps), eps={INTERFACE_EPS_UM} um, ~8% corner over-count",
            "calibration_note": "percentiles and residuals come from the whole "
                                "section (44,134 scored cells), never from this patch",
        },
        "geometry": {
            "centre_um": [round(cx, 2), round(cy, 2)],
            "radius_um": round(radius, 2),
            "bbox_um": [round(float(xy[sel, 0].min()), 2), round(float(xy[sel, 1].min()), 2),
                        round(float(xy[sel, 0].max()), 2), round(float(xy[sel, 1].max()), 2)],
            "n_cells": len(cells),
            "n_occluded_neighbours": len(occluded),
        },
        "summary": {
            "composition": {str(k): int(v) for k, v in comp.items()},
            "n_concordant_exact": sum(1 for c in cells if c["identity"]["agreement"] == "concordant_exact"),
            "n_concordant_lineage": sum(1 for c in cells if c["identity"]["agreement"] == "concordant_lineage"),
            "n_identity_conflict": sum(1 for c in cells if c["identity"]["agreement"] == "conflict"),
            "n_scored": sum(1 for c in cells if c["qc"]["scored"]),
            "n_contact_pairs_internal": len({
                tuple(sorted((c["cell_id"], e["cell_id"])))
                for c in cells for e in c["contacts"]
                if not e.get("outside_patch") and not e.get("occluded")}),
            "n_contacts_to_outside_patch": sum(
                1 for c in cells for e in c["contacts"] if e.get("outside_patch")),
            "n_contacts_to_occluded": sum(
                1 for c in cells for e in c["contacts"] if e.get("occluded")),
            "mean_contacts_per_cell": round(
                sum(len(c["contacts"]) for c in cells) / max(len(cells), 1), 2),
        },
        "occluded_neighbours": sorted(occluded.values(), key=lambda e: e["cell_id"]),
        "cells": cells,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {args.out}  ({args.out.stat().st_size/1024/1024:.2f} MiB)")
    print(f"  {patch_id}: {len(cells)} cells, radius {radius:.1f} um, "
          f"{doc['summary']['n_contact_pairs_internal']} internal contact pairs, "
          f"{len(occluded)} occluded neighbours")
    print("  composition:", dict(list(doc["summary"]["composition"].items())[:6]))


if __name__ == "__main__":
    main()
