#!/usr/bin/env python3
"""Fit the reference distributions the engine needs to interpret a UCell score.

Reads only LUAD3_TLS_GO20_UCell.h5ad. Writes rulebook/calibration.json.

Why this exists
---------------
A raw UCell value is not a state variable in this dataset: it tracks how many
genes were detected in the cell (Spearman rho up to 0.81 *within* a single cell
type; see MANUAL.md section 8). Two derived quantities are therefore required
before any score may enter a rule:

  percentile   -- rank of the raw value within the same cell type
  depth_residual -- raw value minus the median of its (cell type, depth decile)

Both need reference distributions fitted on a large population. They are fitted
here on all 44,134 scored cells of the section, NOT on the simulation patch:
a 1,000-cell patch cannot estimate its own percentiles.

Usage
-----
    python scripts/build_calibration.py --h5ad LUAD3_TLS_GO20_UCell.h5ad \
                                        --out rulebook/calibration.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np
from scipy.stats import spearmanr

N_DEPTH_DECILES = 10
PERCENTILE_GRID = list(range(0, 101, 10))

# Genes that SPLIT removes almost entirely from purified_raw, the layer UCell ranked.
# A signature containing one of these was scored with that gene silently absent, so its
# nominal panel coverage overstates what actually contributed. See MANUAL.md s9.3.
LAYER_DELETED_GENES = {"HLA-A", "HLA-DPB1", "PTP4A1", "HLA-DQB2", "AKR1C1", "KRT81", "DAPL1"}

# Which signatures may not stand alone as evidence, and why. See MANUAL.md s8.2.
COVERAGE_FLAGS = {
    "GOBP_T_CELL_ACTIVATION": "identity_confounded",
    "GOBP_B_CELL_ACTIVATION": "identity_confounded",
    "GOBP_LYMPHOCYTE_DIFFERENTIATION": "identity_confounded",
    "GOBP_LEUKOCYTE_CELL_CELL_ADHESION": "identity_confounded",
    "GOBP_PHAGOCYTOSIS": "identity_confounded",
    "GOBP_T_CELL_MEDIATED_CYTOTOXICITY": "identity_confounded",
    "GOBP_MITOTIC_CELL_CYCLE": "low_coverage",
    "GOBP_RESPONSE_TO_ENDOPLASMIC_RETICULUM_STRESS": "low_coverage",
    "GOBP_RESPONSE_TO_OXIDATIVE_STRESS": "low_coverage",
    "GOBP_SPROUTING_ANGIOGENESIS": "low_coverage",
    "GOBP_APOPTOTIC_SIGNALING_PATHWAY": "low_coverage",
    "GOBP_RESPONSE_TO_TRANSFORMING_GROWTH_FACTOR_BETA": "low_coverage",
    "GOBP_RESPONSE_TO_OXYGEN_LEVELS": "low_coverage",
    "GOBP_RESPONSE_TO_TUMOR_NECROSIS_FACTOR": "low_coverage",
}


def categorical(obs: h5py.Group, name: str) -> np.ndarray:
    grp = obs[name]
    cats = np.array([c.decode() if isinstance(c, bytes) else c for c in grp["categories"][:]])
    codes = grp["codes"][:]
    return np.where(codes >= 0, cats[np.clip(codes, 0, None)], "NA")


def decode(arr) -> list:
    return [v.decode() if isinstance(v, bytes) else v for v in arr[:]]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--h5ad", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--annotation", default="cell_type_fine",
                    help="obs column used to group cells. The bundle ships "
                         "cell_type_fine; first_type is a valid alternative and "
                         "the two agree on only 34.9%% of cells (MANUAL.md s4).")
    ap.add_argument("--skip-checksum", action="store_true")
    args = ap.parse_args()

    f = h5py.File(args.h5ad, "r")
    obs = f["obs"]

    scored = obs["go20_scored"][:]
    labels = categorical(obs, args.annotation)
    depth = obs["n_genes_by_counts"][:].astype(float)

    gs = f["uns"]["go20_gene_sets"]
    sig_meta = {}
    for process, go_id, geneset, n_set, n_avail, cov, genes, col in zip(
        decode(gs["process"]), decode(gs["go_id"]), decode(gs["geneset"]),
        gs["n_genes_geneset"][:], gs["n_genes_available"][:],
        gs["coverage_pct"][:], decode(gs["genes_available"]), decode(gs["score_column"]),
    ):
        gene_list = genes.split(";")
        deleted = sorted(set(gene_list) & LAYER_DELETED_GENES)
        sig_meta[geneset] = {
            "process": process,
            "go_id": go_id,
            "obs_column": col,
            "n_genes_geneset": int(n_set),
            "n_genes_on_panel": int(n_avail),
            "panel_coverage": round(float(cov) / 100.0, 5),
            "n_genes_deleted_by_layer": len(deleted),
            "genes_deleted_by_layer": deleted,
            "n_genes_effective": int(n_avail) - len(deleted),
            "effective_coverage": round((int(n_avail) - len(deleted)) / int(n_set), 5),
            "genes_on_panel": gene_list,
            "coverage_flag": COVERAGE_FLAGS.get(geneset, "sufficient"),
        }

    out = {
        "calibration_version": "1.0.0",
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "source": {
            "file": args.h5ad.name,
            "sha256": None if args.skip_checksum else sha256(args.h5ad),
            "annotation_column": args.annotation,
        },
        "fitted_on": {
            "population": "all cells with go20_scored == true",
            "n_cells": int(scored.sum()),
            "note": "Reference distributions are fitted on the whole section. "
                    "A simulation patch is too small to estimate its own "
                    "percentiles and must import these.",
        },
        "depth_covariate": {
            "obs_column": "n_genes_by_counts",
            "matrix": "raw_counts",
            "caveat": "UCell ranked purified_raw, whose non-zero count per cell "
                      "differs (section-wide median 31 vs 33). Using "
                      "n_genes_by_counts makes the depth correlations reported "
                      "here conservative.",
            "n_deciles": N_DEPTH_DECILES,
        },
        "signatures": sig_meta,
        "cell_types": {},
    }

    for label in sorted(set(labels[scored])):
        mask = scored & (labels == label)
        d = depth[mask]
        edges = [float(np.percentile(d, q)) for q in np.linspace(0, 100, N_DEPTH_DECILES + 1)]
        # strictly increasing edges, so searchsorted gives a well-defined decile
        for i in range(1, len(edges)):
            if edges[i] <= edges[i - 1]:
                edges[i] = edges[i - 1] + 1e-9
        decile = np.clip(np.searchsorted(edges[1:-1], d, side="right"), 0, N_DEPTH_DECILES - 1)

        entry = {
            "n_scored": int(mask.sum()),
            "median_n_genes_by_counts": float(np.median(d)),
            "depth_decile_edges": [round(e, 4) for e in edges],
            "signatures": {},
        }

        for geneset, meta in sig_meta.items():
            v = obs[meta["obs_column"]][:][mask].astype(float)
            rho = spearmanr(v, d).statistic
            med_by_decile = [
                round(float(np.median(v[decile == k])), 5) if (decile == k).any() else None
                for k in range(N_DEPTH_DECILES)
            ]
            entry["signatures"][geneset] = {
                "percentile_edges": [round(float(np.percentile(v, q)), 5) for q in PERCENTILE_GRID],
                "percentile_grid": PERCENTILE_GRID,
                "zero_fraction": round(float((v == 0).mean()), 4),
                "median": round(float(np.median(v)), 5),
                "median_by_depth_decile": med_by_decile,
                "rho_vs_depth_within_type": round(float(rho), 3),
                "coverage_flag": meta["coverage_flag"],
                "admissible_use": (
                    ["rank_within_type"]
                    if meta["coverage_flag"] == "sufficient"
                    else ["rank_within_type_with_corroboration"]
                ),
                "inadmissible_use": [
                    "absolute_activation_level",
                    "cross_process_comparison",
                    "event_probability",
                    "threshold_on_raw_value",
                ],
            }
        out["cell_types"][label] = entry

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {args.out}  ({args.out.stat().st_size/1024:.0f} KiB, "
          f"{len(out['cell_types'])} cell types x {len(sig_meta)} signatures)")


if __name__ == "__main__":
    main()
