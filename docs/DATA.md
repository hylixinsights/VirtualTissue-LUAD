# Data, provenance and reconstruction

This project uses one supplied human LUAD3 Xenium section: 133,464 annotated cells, 150,055 segmentation polygons, 302 panel genes and 44,134 scored cells. The raw delivery is intentionally outside the project directory. A new checkout requires authorized access to those inputs; no public download URL or redistribution permission is inferred here.

Required local files:

- `LUAD3_TLS_GO20_UCell.h5ad`
- `cell_boundaries.csv`

Default data directory: the parent of this project. Override it with `--data-dir`. The builder requires the H5AD hash recorded in the supplied specification: `341e6e591e9dd6cd3f617919ac0e0683ebc5632f7879e25d6a9756d611795752`. A different specimen needs an explicitly revised specification/calibration, not a renamed input file.

The H5AD stores `obsm/spatial` in µm. Its original mirrored coordinates are not used. Cell IDs join observations to boundaries. Polygon repair, if needed, is listed explicitly. The count and contact checks compare the new B26 reconstruction with the delivered `examples/patch_B26.json` when that reference is present; a clean release does not bundle per-cell patch records.

| Property | B26 | B27 |
|---|---:|---:|
| ROI cells | 1,000 | 1,000 |
| Scored ROI cells | 983 | 695 |
| Internal contact pairs | 2,883 | 2,975 |
| CD8–tumor pairs | 19 | 2 |
| CAF–tumor pairs | 45 | 183 |
| Frozen annotated halo cells | 296 | 298 |
| Unannotated polygons in the halo/domain | 145 | 30 |
| Unannotated partners directly contacting ROI cells | 123 | 24 |
| Annotated external partners directly contacting ROI cells | 73 | 71 |

The larger count of unannotated domain polygons includes objects in the 30 µm halo, beyond direct contacts. Context objects are never added to the 1,000-cell ROI denominator.

Expression evidence uses positive entries in `purified_raw`, respecting sparse-matrix encoding and removing explicit zeros. The panel membership vector preserves not-assayed versus not-detected semantics. The frozen calibration uses `n_genes_by_counts` from raw-count QC to define depth deciles; this is not silently replaced by a purified-expression depth statistic. It is a known limitation of the reference calibration.

Scores are observations at the initial time, not dynamic pathway concentrations. Percentile by cell type is descriptive. Depth residual is raw minus the stored type/depth-decile median. Original coverage flags remain available alongside the stricter operational flag. The small panel and lineage confounding prevent any score from being sufficient evidence by itself. Layer-sensitive HLA observations and anomalous marker patterns documented in the manual remain limitations; this runtime does not infer antigen recognition or protein competence from them.

`outputs/atlas_B*.json.gz` contains per-cell experimental derivatives and is ignored by Git. `outputs/audit_B*.json` records reconstruction metadata, input hashes and baseline rule summaries. Private episodes are also ignored. The allowlisted release contains aggregated calibration and the supplied rulebook/manual, but excludes raw input, per-cell examples, atlases and episodes. Review data terms before changing that boundary for publication.
