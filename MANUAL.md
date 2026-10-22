# A cell-level rulebook for a LUAD virtual tissue driven by Jev

**Version 1.0 — 22 September 2026**

A specification for running per-cell, real-time micro-decisions inside a real human lung adenocarcinoma section, using a TypeSafe System One model (Jev) as the judgement layer and an engine that owns geometry, resources, time and death.

This manual has one governing principle: **every field the simulation shows a model, and every rule the engine enforces, carries its provenance.** A measured quantity, a transferred mechanism and a scenario construct are three different things, and the difference is never allowed to blur. Most of what follows is about keeping that distinction while still building something that runs.

It supersedes the internal drafts v0.1 (literature only), v0.2 (sample-grounded, centroid-approximated contact) and v0.2.1 (measured contact).

---

## Contents

1. [What this is, and how to use it](#1-what-this-is-and-how-to-use-it)
2. [The sample](#2-the-sample)
3. [Evidence conventions](#3-evidence-conventions)
4. [Cell identity is a set, not a label](#4-cell-identity-is-a-set-not-a-label)
5. [Measured composition](#5-measured-composition)
6. [Contact and geometry](#6-contact-and-geometry)
7. [Tertiary lymphoid structures](#7-tertiary-lymphoid-structures)
8. [Pathway signatures and their calibration](#8-pathway-signatures-and-their-calibration)
9. [Measurement semantics](#9-measurement-semantics)
10. [The interaction registry and what the panel can see](#10-the-interaction-registry-and-what-the-panel-can-see)
11. [The simulation patch](#11-the-simulation-patch)
12. [Cell repertoires](#12-cell-repertoires)
13. [Rules](#13-rules)
14. [Perturbations](#14-perturbations)
15. [Jev integration](#15-jev-integration)
16. [Engine constraints](#16-engine-constraints)
17. [Validation](#17-validation)
18. [What remains unknown](#18-what-remains-unknown)
19. [Repository contents](#19-repository-contents)
20. [References](#20-references)

---

## 1. What this is, and how to use it

### 1.1 The three layers

| Layer | Owns | Never does |
| --- | --- | --- |
| **Engine** | Geometry, contact graph, fields, resources, timers, cycle, damage, death, clearance, event ordering, audit | Ask a model to decide whether a cell dies, divides, or what it is |
| **Rulebook** (`rulebook/rulebook.json`) | Which actions exist, which identities may take them, which conditions gate them, which of those conditions are measured, what each perturbation adds | Contain patient data, or travel to the model |
| **Jev** | Rank admissible behaviours the engine has already validated, and report a calibrated distribution over them | Generate text, resolve identity, supply a rate, or invent a value the engine marked unmeasured |

The rulebook is the contract between the first and the third. It is read by the engine at startup and never transmitted: the engine projects a small per-decision `state` object from it plus the cell's live condition (§15.3).

### 1.2 Reading order

A modeller implementing the engine should read §§4, 6, 9, 13, 15, 16. A biologist checking whether the model is defensible should read §§2, 3, 5, 7, 8, 10, 17. Anyone about to quote a number from this manual in a paper should read §3 first, then §18.

### 1.3 The three findings that shape everything else

**Contact is rare where the textbook says it should be common.** Measured from segmentation polygons, 1.38 % of cytotoxic CD8 T cells touch a tumour cell anywhere in the section; the median CD8 sits 104 µm of solid tissue away. Under strict identity handling, in the 1,000-cell reference patch chosen specifically because it contains both a lymphoid follicle and a tumour nest, exactly **one** cell is eligible for the canonical cytotoxic rule (§13.3). A simulation that produces frequent CD8-mediated killing is not reproducing this specimen.

**A pathway score here is largely a readout of sequencing depth.** Spearman ρ between a UCell value and the number of detected genes reaches 0.81 *within* a single cell type. No raw score may enter a threshold; only a percentile within cell type and depth decile may (§8.3, constraint H13).

**Identity itself is uncertain, and the uncertainty is structured.** The two annotations shipped with the object agree exactly on 34.9 % of cells and at lineage level on 62.6 %. The gap between those two numbers is vocabulary, not biology, and confusing them freezes entire compartments for the wrong reason (§4).

---

## 2. The sample

LUAD3 is one 10x Xenium section of human lung adenocarcinoma, delivered as `LUAD3_TLS_GO20_UCell.h5ad` (sha256 `341e6e59…`) derived from `Xenium_LUAD_No3_annotated.h5ad`, plus `cell_boundaries.csv`.

| Property | Value |
| --- | --- |
| Annotated cells | 133,464 |
| Segmented cells (polygons) | 150,055 |
| Panel | 302 genes |
| Section extent | 7,907.6 × 6,754.3 µm |
| Cells with pathway scores | 44,134 (exactly those inside the 28 geodesic candidate regions) |
| Median polygon area | 104.2 µm² |
| Median nearest-neighbour distance | 8.31 µm |
| Patients / sections / replicates | 1 / 1 / 0 |

Scoring used pyUCell 0.7.3 on layer `purified_raw` (SPLIT-corrected), `max_rank=100`, `ties_method='average'`, `missing_genes='skip'`, no smoothing. Gene sets are MSigDB 2026.1.Hs C5:GO:BP, twenty processes selected on panel coverage before any candidate score was inspected [D02, D03].

**n = 1.** Everything measured here describes this section. None of it estimates LUAD as a disease. This is why the evidence class `D-LUAD3` exists and why it is simultaneously the strongest evidence for initialising the simulation and the weakest for any general claim.

### 2.1 "Detected genes per cell" has three correct values

| Definition | median | p95 | Where it appears |
| --- | --- | --- | --- |
| `obs.n_genes_by_counts` (from `raw_counts`, all cells) | 33 | 68 | The obs column any analyst reaches for |
| non-zero in `purified_raw`, all cells | 31 | 64 | The delivery README |
| non-zero in `purified_raw`, scored cells | 29 | 54 | `provenance.json` |

All three are right for their own definition. The third governs score interpretation, because it counts genes in the matrix UCell actually ranked. The depth correlations in §8.3 were computed against the first, which makes them conservative.

---

## 3. Evidence conventions

| Code | Source | Use |
| --- | --- | --- |
| `D-LUAD3` | Measured in this specimen | Initialise the simulation. Never generalise. |
| `H-LUAD` | Human lung adenocarcinoma literature | Closest disease prior; keep stage, site and treatment context |
| `H-NSCLC` | Human NSCLC, possibly mixed histology | Transfer conditional on histology |
| `M-LUNG` | Experimental lung-tumour model | Causal support in that model; human kinetics unmeasured |
| `X-TISSUE` | Another tumour or tissue | Transferred mechanism, to be assessed in LUAD |
| `METHOD` | Methods paper or official documentation | Measurement and interface limits |
| `SIM` | Explicit simulation design choice | Must never be presented as an observation |

Four **measurability levels** gate every condition in a rule:

- `observable` — all components on the panel and detectable in the relevant cell type
- `partially_observable` — some components on the panel
- `assumed_only` — nothing on the panel; usable only inside a named assumed-competence profile
- `unobservable_by_design` — needs protein, V(D)J, flux or time; no Xenium re-analysis can supply it

A clinical association can support a compositional expectation. It never supplies a per-cell transition rate.

---

## 4. Cell identity is a set, not a label

### 4.1 Two annotations, two vocabularies

The object carries four annotation columns. `leiden` and `cell_type` are the same ten-cluster partition under different names. `cell_type_fine` differs from `cell_type` only inside the T compartment (3,756 cells moved `T_CD4 → T_CD8_cytotoxic`, 91 the reverse). `first_type` is a **different** annotation with a different vocabulary.

| Agreement | Value | Cells |
| --- | --- | --- |
| Exact label | 34.85 % | 46,513 |
| Lineage level | 62.58 % | 83,525 |

The gap between these two numbers is almost entirely vocabulary. Six labels exist only in `cell_type_fine` (`CAF`, `Fibroblast`, `Macrophage_SPP1`, `Plasma_cell`, `T_CD8_cytotoxic`, `Tumor_proliferating`) and six only in `first_type` (`DC`, `Mast_NK`, `Myeloid`, `Stromal`, `T_CD8`, `Undefined`).

**This has a consequence that is easy to get wrong.** A plasma cell *cannot* be exact-concordant, because `first_type` has no `Plasma_cell` category at all. The same holds for CAF, fibroblast and proliferating tumour. An early version of the rulebook gated plasma-cell secretion on exact agreement and thereby froze the entire 12,907-cell plasma compartment — a vocabulary artefact presented as biology. The rulebook now distinguishes three states: `concordant_exact`, `concordant_lineage`, `conflict`.

### 4.2 Where the two annotations genuinely disagree

At lineage level, after mapping both vocabularies to a common six-way scheme:

| Disagreement | Cells |
| --- | --- |
| `first_type` stromal → `cell_type_fine` T | 10,420 |
| `first_type` B lineage → `cell_type_fine` T | 5,705 |
| `first_type` endothelial → `cell_type_fine` T | 5,333 |
| `first_type` tumour → `cell_type_fine` stromal | 5,121 |
| `first_type` stromal → `cell_type_fine` B lineage | 2,509 |

These are real: a cell called endothelium by one method and a T cell by the other is not a naming difference.

### 4.3 The policy

A cell carries both labels. Rules declare one of two conflict policies:

- **`require_all_candidates_in_lineage`** — every candidate label must map to a lineage the rule accepts. This is the default for irreversible or damaging actions. A cell called `T_CD8_cytotoxic` by one column and `B_cell` by the other may not kill anything.
- **`allow_any_candidate_match`** — one matching candidate suffices, and the state carries `identity_agreement` so the model can weigh the uncertainty. Used for reversible, non-damaging actions.

The effect is large and deliberate. In the reference patch, the CD8 degranulation rule is eligible for 29 cells under the permissive policy and **1** under the strict one (§13.3). That difference is the honest cost of the annotation problem, made visible rather than hidden.

Populations with **no label in either column** — AT1, AT2, club, ciliated, basal, NK, mast, neutrophil, pDC, γδ T, MAIT, ILC, pericyte, lymphatic endothelium, Treg — are instantiated as `not_annotated` with maintenance only. Absence of a label is not absence from the tissue.

---

## 5. Measured composition

Whole section, both annotations:

| `cell_type_fine` | n | % | | `first_type` | n | % |
| --- | --- | --- | --- | --- | --- | --- |
| Tumor | 22,987 | 17.2 | | Tumor | 35,245 | 26.4 |
| T_CD8_cytotoxic | 20,082 | 15.1 | | B_cell | 31,479 | 23.6 |
| B_cell | 17,990 | 13.5 | | Stromal | 30,435 | 22.8 |
| Fibroblast | 16,428 | 12.3 | | Endothelial | 17,761 | 13.3 |
| T_CD4 | 13,487 | 10.1 | | T_CD4 | 7,805 | 5.9 |
| Plasma_cell | 12,907 | 9.7 | | Myeloid | 2,621 | 2.0 |
| Endothelial | 11,182 | 8.4 | | DC | 2,577 | 1.9 |
| Macrophage_SPP1 | 7,651 | 5.7 | | T_CD8 | 2,304 | 1.7 |
| CAF | 6,592 | 4.9 | | Undefined | 1,898 | 1.4 |
| Tumor_proliferating | 4,158 | 3.1 | | Mast_NK | 1,339 | 1.0 |

An abundant malignant compartment, abundant T and B cells, substantial fibroblast/CAF and a large plasma-cell fraction are all compatible with human LUAD and NSCLC atlases [R05, R06, R08]. Two things do **not** transfer: the CD8:CD4 ratio inverts between annotations (1.49 vs 0.30), and several populations have no category at all.

### 5.1 Immune exclusion, quantified

Composition by distance to the nearest tumour core (%):

| Band (µm) | n | Tumour | CAF | Fibroblast | T_CD4 | T_CD8 | B | Plasma | Macro | Endo |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 (core) | 22,598 | 85.0 | 3.5 | 7.1 | 0.3 | 0.4 | 0.0 | 1.2 | 2.1 | 0.4 |
| 0–25 | 9,013 | 5.7 | **24.8** | 29.6 | 11.6 | 4.3 | 1.7 | 9.2 | 6.3 | 6.7 |
| 25–50 | 12,114 | 5.2 | 6.3 | 21.3 | 16.7 | 11.8 | 5.5 | 14.1 | 6.5 | 12.6 |
| 50–100 | 19,172 | 11.1 | 4.3 | 15.1 | 13.5 | 14.9 | 9.8 | 12.7 | 6.2 | 12.4 |
| 100–250 | 33,651 | 10.9 | 4.2 | 12.2 | 12.5 | 15.7 | 16.9 | 11.5 | 6.2 | 9.9 |
| 250–500 | 15,880 | 5.4 | 3.1 | 9.6 | 12.3 | 15.3 | 26.1 | 11.0 | 7.0 | 10.1 |
| > 500 | 21,036 | 0.7 | 0.3 | 4.9 | 7.7 | **36.2** | 25.9 | 9.7 | 6.8 | 7.8 |

CAFs occupy the 0–25 µm rim; lymphocytes rise monotonically with distance. This is consistent with matrix-dependent T-cell positioning in human lung tumours [R18], but no matrix-architecture channel was measured here, so the mechanism is a hypothesis the simulation may test, not a finding the data support.

---

## 6. Contact and geometry

`cell_boundaries.csv` supplies 150,055 polygons (≤ 13 vertices each) in the `obsm['spatial']` frame. Contact is therefore a **measurement**, not an approximation.

### 6.1 The definition

Pairwise minimum distance between polygon boundaries:

| Gap | Pairs (annotated cells) |
| --- | --- |
| = 0 (touching) | 55,425 |
| ≤ 0.25 µm | 349,703 |
| **≤ 1.0 µm** | **377,270** |
| ≤ 2.0 µm | 406,603 |
| ≤ 5.0 µm | 527,090 |

The count plateaus between 0.25 and 1 µm (+7.9 %) and climbs again after. **`gap ≤ 1.0 µm` is the definition.** The 0.25 µm variant changes no conclusion in this manual.

Two structural facts follow:

- Cells have **6.11 contacts on average** (median 5–6): a planar packing.
- Essentially the whole perimeter of every cell abuts another segmented cell. **There is no free space.** A cell cannot move or divide without displacing a neighbour, and "free membrane" is not a meaningful model variable.

### 6.2 Who touches whom

P(≥ 1 contact with the column type), rows = focal:

| Focal ↓ | B | CAF | Endo | Fibro | Macro | Plasma | CD4 | CD8 | Tumour |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B_cell | 0.916 | 0.012 | 0.144 | 0.074 | 0.181 | 0.112 | 0.260 | 0.515 | 0.007 |
| CAF | 0.028 | 0.762 | 0.181 | 0.642 | 0.139 | 0.217 | 0.524 | 0.097 | **0.598** |
| Endothelial | 0.158 | 0.107 | 0.793 | 0.462 | 0.249 | 0.374 | 0.411 | 0.435 | 0.040 |
| Fibroblast | 0.064 | 0.335 | 0.344 | 0.769 | 0.208 | 0.384 | 0.392 | 0.257 | 0.235 |
| Macrophage_SPP1 | 0.251 | 0.104 | 0.298 | 0.337 | 0.514 | 0.379 | **0.402** | **0.483** | 0.138 |
| Plasma_cell | 0.150 | 0.121 | 0.323 | 0.457 | 0.277 | 0.745 | 0.473 | 0.447 | 0.061 |
| T_CD4 | 0.224 | 0.303 | 0.356 | 0.449 | 0.281 | 0.445 | 0.801 | 0.449 | 0.090 |
| T_CD8_cytotoxic | 0.400 | 0.034 | 0.307 | 0.216 | 0.271 | 0.311 | 0.347 | 0.820 | **0.014** |
| Tumor | 0.006 | 0.294 | 0.026 | 0.206 | 0.111 | 0.045 | 0.065 | 0.016 | 0.985 |
| Tumor_proliferating | 0.005 | 0.374 | 0.029 | 0.186 | 0.094 | 0.027 | 0.108 | 0.017 | 0.336 |

Polygon gap to the **nearest** tumour cell: CAF 0.1 µm (median), T_CD4 42.7, Plasma 51.0, Macrophage 52.1, **T_CD8 104.3**, B 111.6.

Homotypic enrichment over section frequency: `Tumor_proliferating` 21.6×, B 5.0×, CAF 4.6×, endothelium 4.0×, plasma 3.3×, CD8 3.0×, macrophage 3.0×.

### 6.3 What the geometry forbids

- **CD8 ↔ tumour is rare.** 277 of 20,082 CD8 T cells touch a tumour cell. The cytotoxic rule is spatially ineligible for ~99 % of them.
- **CAF is the tumour's interface.** 59.8 % touch tumour; 23.0 % of a CAF's contacts and 20.8 % of its interface length are tumour. Tumour–stroma signalling is the circuit that is eligible at scale — and, per §10, almost entirely unmeasurable on this panel.
- **Macrophages are the connector.** 48.3 % touch a CD8 T cell, 40.2 % a CD4 T cell, 25.1 % a B cell. The antigen-presentation circuits they support are the most spatially plausible in the section.
- **The B compartment is self-contained.** 67.1 % of a B cell's interface is B–B. Inside a follicle a diffusible field is effectively uniform and offers no gradient to follow.
- **Tumour nests are closed.** 98.5 % of tumour cells touch another tumour cell; the only routine non-tumour partner is CAF (29.4 %).

### 6.4 Why centroid proximity is forbidden

Treating the polygon graph as truth and a centroid threshold as a classifier:

| Threshold | Precision | Recall | F1 |
| --- | --- | --- | --- |
| ≤ 10 µm | 0.905 | 0.357 | 0.512 |
| ≤ 12 µm | 0.792 | 0.503 | 0.615 |
| **≤ 15 µm** | 0.636 | 0.682 | **0.658** |
| ≤ 20 µm | 0.441 | 0.875 | 0.587 |
| ≤ 30 µm | 0.223 | 0.993 | 0.365 |

No threshold works, and the error is **systematic in cell size**. Median polygon area spans five-fold: CAF 227.0 µm², Fibroblast 153.5, Tumour 142.4, T_CD4 138.6, Plasma 107.7, Macrophage 96.2, **T_CD8 60.6, B_cell 43.4**. Large cells reach past their centroids, so proximity under-counts their contacts by ~2× (CAF→Tumour 0.598 true vs 0.330 at 15 µm); small dense cells have many centroids nearby that are not neighbours, so proximity over-counts by up to 1.8× (B→Macrophage 0.181 true vs 0.321).

The 30 µm neighbourhood survives as a **signalling neighbourhood** for soluble mediators and nothing else: at 30 µm, precision as a contact test is 0.223, and a B cell has 52.3 neighbours within 30 µm against 6.4 true contacts. `contacts` and `neighbourhood_30um` are separate fields and never interchangeable.

### 6.5 Occluded neighbours

`cell_boundaries.csv` has 16,591 more polygons than the AnnData has cells: segmented cells that QC removed (median area 74.7 µm² vs 104.2 for retained). They still occupy space.

7.5 % of all contacts are to such a cell, and **28.2 % of annotated cells have at least one**. The rate is uneven — endothelium 12.9 %, fibroblast 12.8 %, plasma 12.1 %, CD8 10.9 %, B 4.5 %, tumour 1.4 % — so deleting them would make the tissue porous in a biased way. They are instantiated as `occluded_neighbour`: they occupy space, block movement and can receive imposed damage, but have no identity, no state, no repertoire and never a Jev call.

---

## 7. Tertiary lymphoid structures

28 geodesic candidates hold 44,134 cells (18,879 core + 25,255 surroundings). `TLS_stage_name` labels twelve cores mature, fifteen primary-follicle, one early aggregate.

Two facts must be recorded before the maturity label is used for anything.

**The core is the annotation.** All 18,879 core cells are `first_type == B_cell` (100.0 %). The core mask *is* a B-cell mask, so "TLS cores are B-cell-rich" is not a finding. Under `cell_type_fine` the same cores are 71.2 % B, 10.9 % CD8, 8.3 % plasma, 4.2 % macrophage.

**`TLS_stage` and `TLS_stage_name` are different variables.** The integer has counts 87,790 / 675 / 26,773 / 18,226; the name 114,581 / 104 / 11,860 / 6,919. Cross-tabulated, `TLS_stage == 2` contains 14,913 cells named `Background`. Do not use them interchangeably.

**Maturity has no transcriptional correlate here.** B cells in mature versus primary cores:

| Process (B cells, core only) | Primary (n = 9,101) | Mature (n = 4,331) |
| --- | --- | --- |
| B cell activation | 0.290 | 0.290 |
| Lymphocyte differentiation | 0.187 | 0.188 |
| Mitotic cell cycle | 0.113 | 0.112 |
| Antigen processing | 0.133 | 0.160 |
| median detected genes | 32 | 33 |

The only visible gap sits inside a one-gene difference in median depth. Maturity is an architectural label the simulation records as region metadata with `evidence: delivered_label_uncorroborated`; **no rule may condition a cell's action on it** until an independent criterion exists.

Six candidates staged mature or primary have cores dominated by plasma cells under `cell_type_fine` — B8 (59.8 %), B18 (63.1 %), B19 (57.4 %), B21 (63.5 %), B23 (49.3 %), B28 (49.0 %). These are plausibly extrafollicular plasma-cell aggregates, the entity described for LUAD by Zhan et al. [R15]. Annotate them separately; do not enable a germinal-centre module in them. Indeed, the GC module is disabled everywhere: `AICDA`, `BCL6`, `CR2` and `FCER2` are all absent from the panel and no clonal state exists.

`CXCL13` is detected in 50.6 % of B cells, 9.1 % of CD4 and 8.8 % of CD8 — the inverse of the canonical Tfh/stromal pattern, and a pattern to verify before `CXCL13` is used as a Tfh marker or a B-attracting source. `FDCSP`, an FDC marker, is detected in 31.7 % of B cells, which is inconsistent with a sparse FDC network and consistent with spillover.

---

## 8. Pathway signatures and their calibration

### 8.1 Coverage is low everywhere

No process exceeds 16 % of its GO definition. Extremes: ECM disassembly 15.3 %, T-cell-mediated cytotoxicity 13.3 %, antigen processing 13.1 % — down to EMT 8.5 %, apoptotic signalling 4.5 %, **mitotic cell cycle 1.9 % (18 of 959 genes)**, of which only six are cycle machinery.

### 8.2 Six signatures are lineage identity in disguise

| Process | Identity genes inside it | Consequence |
| --- | --- | --- |
| T cell activation | `CD3E, CD4, CD8A, LCK, LAT, PTPRC, CD74` | A resting T cell scores high for being a T cell |
| B cell activation | `CD19, BANK1, MZB1, POU2AF1, SPIB, CD74` | B and plasma cells score high by lineage |
| Phagocytosis | `MARCO, MSR1, ITGAM, ITGAX, PECAM1` | Myeloid identity, not engulfment |
| Lymphocyte differentiation | `CD3E, CD4, CD8A, CD19, PTPRC` | Same problem |
| Leukocyte cell-cell adhesion | largely the T-activation list | Correlates with it by construction |
| **T cell mediated cytotoxicity** | `CD1C, CD1E, FCGR2B, HLA-A, NECTIN2, PVR, PTPRC, PRF1` | **Only `PRF1` is an effector gene.** `NECTIN2` and `PVR` are *target*-side ligands enriched in tumour cells (27.8 % / 31.7 %), so a tumour cell can score high on "cytotoxicity". `GZMA` and `GZMB` are on the panel but not in this GO set |

Measured: median cytotoxicity score is 0.124 in CD8 and 0.076 in tumour, with 12.5 % and 36.8 % exact zeros — nowhere near enough separation to gate a killing rule. The rulebook forbids this substitution explicitly, and the forbidden substitutions travel in the Jev `state` so the model is told not to use them either.

### 8.3 Scores track detection depth

Spearman ρ with `n_genes_by_counts`, overall and within single cell types:

| Process | all | in B | in CD8 | in Tumour |
| --- | --- | --- | --- | --- |
| T cell activation | 0.725 | 0.713 | **0.814** | 0.719 |
| Apoptotic signalling | 0.708 | 0.652 | 0.732 | 0.731 |
| Leukocyte adhesion | 0.672 | 0.681 | 0.789 | 0.662 |
| Lymphocyte differentiation | 0.661 | 0.697 | 0.764 | 0.685 |
| Inflammatory response | 0.646 | 0.659 | 0.751 | 0.683 |
| Response to oxygen levels | 0.599 | 0.501 | 0.510 | 0.647 |
| Mitotic cell cycle | 0.544 | 0.451 | 0.452 | 0.632 |
| T cell mediated cytotoxicity | 0.228 | 0.325 | 0.203 | 0.404 |
| Type II interferon production | 0.179 | 0.254 | 0.381 | 0.245 |

This is not a UCell defect: rank scoring on a 302-gene panel with a median of 29 detected genes behaves this way, because `missing_genes='skip'` means a deeper cell has more signature genes clearing rank 100. Median depth also differs systematically by cell type (Tumour 57, CAF 45, T_CD4 42, B 32, Plasma 26, CD8 26, Fibroblast 23), so cross-type comparison is confounded twice.

### 8.4 What the engine stores instead

| Field | Definition | Use |
| --- | --- | --- |
| `raw` | the delivered value | provenance only; never a threshold |
| `percentile_within_type` | rank within the same cell type | comparison |
| `depth_residual` | raw minus the median of its (cell type, depth decile) | closest available proxy for state beyond depth |
| `coverage_flag` | `sufficient` / `low_coverage` / `identity_confounded` | gates whether the score may be used at all |

`rulebook/calibration.json` holds these reference distributions: per cell type, the depth-decile edges and, per signature, eleven percentile edges, the median by depth decile, the zero fraction and ρ. They are fitted on **all 44,134 scored cells of the section**, never on a simulation patch — a 1,000-cell patch cannot estimate its own percentiles.

**No process has both adequate coverage and no identity confound.** That is the honest summary: these scores order cells *within* a type; they do not measure pathway activity.

---

## 9. Measurement semantics

### 9.1 Three states, never two

| Value | Meaning | Example |
| --- | --- | --- |
| `not_assayed` | absent from the 302-gene panel | `IFNG`, `CSF1R`, `CXCR3`, `IL10`, `FAS`, `TOX`, `AICDA` |
| `not_detected` | on panel, zero in this cell | `PDCD1` in 99.4 % of CD8 T cells |
| `observed` | non-zero in the stated layer | with a spillover flag |

Neither of the first two permits "functionally absent". Conversely, an unmeasured receptor may never be reported as observed because the cell type usually expresses it.

### 9.2 Spillover survives SPLIT correction

SPLIT reduces total counts by 20.8 % but leaves the non-zero mask nearly unchanged (94.0 % of entries retained). Because UCell ranks within the cell, a spillover-positive gene keeps contributing. Measured detection in `purified_raw`:

| Gene | Expected source | Tumour | CAF | Fibroblast | B |
| --- | --- | --- | --- | --- | --- |
| `SFTPB` | alveolar epithelium | 0.908 | **0.842** | **0.655** | 0.144 |
| `NAPSA` | alveolar/LUAD epithelium | 0.964 | **0.748** | 0.273 | 0.124 |
| `EGFR` | epithelium | 0.800 | 0.389 | 0.128 | 0.054 |
| `COL1A1` | fibroblast | 0.788 | 0.901 | 0.543 | 0.101 |
| `PRF1` | cytotoxic lymphocyte | **0.161** | 0.050 | 0.017 | 0.021 |
| `CXCL13` | Tfh / lymphoid stroma | 0.015 | 0.031 | 0.026 | **0.506** |
| `LAMP3` | mature DC / AT2 | **0.269** | 0.107 | 0.037 | 0.021 |

Two direct consequences. `is_LAMP3pos` flags 2,659 cells, highest in tumour (6.4 %) and proliferating tumour (9.2 %), not DC — **it is not a mature-DC flag in this section**. `CCL21_pos` is highest in T cells and endothelium, more consistent with spillover from a `CCL21`-high stromal neighbourhood than with T-cell production; treat it as neighbourhood evidence, not source assignment.

Each observation therefore carries a per-(gene, cell type) spillover prior, and rules may refuse to treat a flagged observation as evidence.

### 9.3 The scoring layer deletes seven genes

This is the subtlest measurement issue in the delivery, and it changes conclusions.

Comparing `raw_counts` with `purified_raw` across all 302 genes, 292 are essentially unchanged (detection ratio > 0.95). Seven are **almost entirely removed**:

| Gene | detection in `raw_counts` | in `purified_raw` | counts kept |
| --- | --- | --- | --- |
| `HLA-A` | 0.628 | 0.004 | 0.3 % |
| `HLA-DPB1` | 0.573 | 0.003 | 0.2 % |
| `PTP4A1` | 0.479 | 0.002 | 0.1 % |
| `HLA-DQB2` | 0.173 | 0.001 | 0.3 % |
| `AKR1C1` | 0.140 | 0.001 | 0.5 % |
| `KRT81` | 0.091 | 0.000 | 0.5 % |
| `DAPL1` | 0.059 | 0.001 | 0.9 % |

**Three of the seven are the MHC genes.** Since the scores were computed on `purified_raw`, six signatures were scored with genes silently missing:

| Process | on panel | deleted | effective |
| --- | --- | --- | --- |
| Antigen processing and presentation | 16 | 3 | 13 |
| Type II interferon production | 12 | 2 | 10 |
| T cell mediated cytotoxicity | 8 | 1 | 7 |
| Leukocyte cell-cell adhesion | 53 | 4 | 49 |
| T cell activation | 58 | 4 | 54 |
| Apoptotic signalling | 29 | 1 | 28 |

Nominal panel coverage overstates these six. `calibration.json` records both nominal and effective coverage for every signature.

**The rule consequence is larger.** The rulebook reads gene evidence from `purified_raw`, the same layer as the scores, so that a rule and a signature never disagree about whether a transcript exists. That makes the MHC-II axis far weaker than `raw_counts` suggests: the macrophage antigen-presentation rule now rests on `CD74` (95.9 % in macrophages, layer-stable), the invariant chain — a marker of the MHC-II *pathway* rather than MHC-II itself. MHC-I loses every component and drops to `assumed_only`. A rule may read `raw_counts` for one of these seven genes only by naming the gene and the layer explicitly.

---

## 10. The interaction registry and what the panel can see

Thirty-four candidate ligand–receptor edges were curated from the literature and checked component-by-component against the panel [R28, R29, R30].

**Against `purified_raw`, the scoring layer, 2 of 34 edges have every component present:**

| Edge | Status |
| --- | --- |
| C01 `CXCL13 → CXCR5` | **complete** |
| C11 `CD80/CD86 ↔ CTLA4` | **complete** |
| C08 `pMHC-II → TCR + CD4` | layer-dependent: complete in `raw_counts`; only `CD74`, `CD4`, `CD3E` survive in `purified_raw` |
| C09 `pMHC-I → TCR + CD8` | layer-dependent; `B2M` also absent |
| C12 `PD-L1 → PD-1` | partial, but `PDCD1` is detected in 0.6 % of CD8 cells |
| C28 `VEGFA → KDR` | partial (`FLT1` absent) — the only near-complete vascular edge |
| C02, C04, C06, C07, C10, C15, C18, C20, C23, C24, C25, C26, C30, C31 | one side absent |
| C03, C05, C13, C14, C16, C17, C19, C21, C22, C27, C29, C32, C33, C34 | absent |

**The entire cytokine-receptor layer is `not_assayed`:** IFNγ and its receptor, IL-12, IL-10, IL-6R, TGFβR, TNFR, IL-1R, CSF1R, CXCR3, CCR2, CXCR4.

A rule whose required components include a `not_assayed` gene resolves to `unknown`, not `false`, and is withheld. Under that policy most of the registry is permanently ineligible on this dataset — which is correct, and is why `assumed_competence_profiles` exist as the only sanctioned way to turn them on, with every decision made under one tagged in the audit record.

A UCell score may never substitute for a missing receptor. A high "response to TGF-β" cannot stand in for `TGFBR2`: its fifteen panel genes include `TGFB1` itself, `COL1A1`, `ACTA2` and `FOS`, making it a fibroblast/tumour identity axis (median 0.330 in CAF, 0.107 in CD8).

---

## 11. The simulation patch

Calibration is fitted on the whole section; the simulation runs on a patch of at most 1,000 cells. Choosing that patch is a modelling decision, because in this section a lymphoid follicle and a tumour nest are rarely near each other.

Scanning windows of the 1,000 cells nearest each candidate core, and counting true contacts inside each window:

| Candidate | radius µm | tumour cells | B cells | CD8 | CD8–tumour contacts | CD8 cells touching tumour | CAF–tumour |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **B26** | **163.7** | **139** | **381** | **205** | **19** | **10** | 45 |
| B9 | 171.7 | 93 | 277 | 262 | 8 | 6 | 48 |
| B24 | 183.2 | 64 | 350 | 159 | 5 | 4 | 38 |
| B27 | 240.0 | 236 | 155 | 73 | 2 | 2 | **183** |
| B5 | 305.8 | 156 | 255 | 110 | 2 | 1 | 71 |
| B17 | 238.8 | 97 | 279 | 113 | 0 | 0 | 80 |

**B26 is the reference patch** and `examples/patch_B26.json` ships it. B27 is the natural secondary patch for tumour–stroma questions.

### 11.1 The reference patch

| Property | Value |
| --- | --- |
| Centre / radius | (1195.6, 4580.6) µm / 163.7 µm |
| Bounding box | 324 × 321 µm |
| Cells | 1,000 (983 with pathway scores) |
| Composition | B 381, CD8 205, Tumor_prolif 126, Fibroblast 70, CD4 59, Macrophage 47, Endothelial 40, Plasma 40, CAF 19, Tumor 13 |
| Identity | 328 exact-concordant, 281 lineage-concordant, 391 conflict |
| Region | 317 cells in a primary-follicle TLS core; 103 in a tumour core |
| Distance to tumour core | 0 – 193 µm (median 53.8) |
| Contacts | 2,883 internal pairs, 150 to cells outside the window, 497 to occluded neighbours |
| Occluded neighbours | 123 |
| Cells with ≥ 1 heterotypic contact | 866 |

Contact rates inside the patch are higher than section-wide, which is why it was chosen: 4.9 % of its CD8 cells touch tumour (against 1.38 % section-wide), 23.7 % of CD4, 89.5 % of CAF, 50.0 % of fibroblasts.

The 150 contacts reaching outside the window are a real boundary condition. The engine must either widen the window, freeze those partners as boundary agents, or record that the boundary is open — it may not silently drop them.

---

## 12. Cell repertoires

Full detail in `rulebook.json`. Summary of what each type may do and what the data withhold:

| Type | n | Capabilities | Principal limits |
| --- | --- | --- | --- |
| `Tumor` | 22,987 | homeostasis, proliferate, MHC-I (assumed), VEGFA, matrix, hypoxia, die | Genotype unknown; nests closed (98.5 % homotypic contact) |
| `Tumor_proliferating` | 4,158 | same | Label rests on `UBE2C` 14.6 % vs 4.2 % and `MKI67` 3.3 % vs 1.4 %; it does **not** have a higher mitotic score than `Tumor` |
| `CAF` | 6,592 | homeostasis, migrate, matrix, VEGFA, hypoxia, die | The tumour-contacting population (59.8 %); largest cells in the section |
| `Fibroblast` | 16,428 | homeostasis, migrate, matrix, hypoxia, die | Lowest detection depth; low scores are partly artefact |
| `B_cell` | 17,990 | homeostasis, migrate, MHC-II, costimulate, hypoxia, die | GC module disabled; `CXCL13` pattern anomalous |
| `Plasma_cell` | 12,907 | homeostasis, secrete Ig, hypoxia, die | Absent from `first_type`; BAFF/APRIL edges unusable; high ER stress is secretory UPR, not damage |
| `T_CD8_cytotoxic` | 20,082 | homeostasis, migrate, degranulate, checkpoint (scenario), hypoxia, die | Exhaustion axis unavailable (`TOX`, `HAVCR2` absent); 1.4 % touch tumour |
| `T_CD4` | 13,487 | homeostasis, migrate, CD40L help, regulate costimulation (scenario), hypoxia, die | No Treg label; `FOXP3` in 4.1 % |
| `Macrophage_SPP1` | 7,651 | homeostasis, migrate, phagocytose, MHC-II, costimulate, VEGFA, hypoxia, die | The connector population; best-supported circuits |
| `Endothelial` | 11,182 | homeostasis, barrier, angiogenic response, hypoxia, die | No HEV evidence; lymphatic not separated; `bv_HH_*` in the object are **B-cell LISA flags, not a vessel mask** |
| `not_annotated` | — | homeostasis, die | For every unlabelled population |
| `occluded_neighbour` | 16,591 | none | Occupies space only |

---

## 13. Rules

Twelve rules ship in v1.0. Each declares eligible identities, a capability, required conditions with their measurability, an identity-conflict policy, its measured eligibility in this section and in the reference patch, forbidden evidence substitutions, effects owned by the engine, and a Jev question template.

### 13.1 Structure

Every rule carries `missing_required_evidence_policy: withhold_action_and_log_unknown`. A condition whose value is unknown resolves to **unknown**, never to false, and the action is withheld from the candidate set with its reason recorded. Every rule carries `event_rate: null` and `calibration_status: not_calibrated`; the schema refuses a non-null rate on an uncalibrated rule.

### 13.2 The twelve

| Rule | Domain | Acting type | Gate highlights |
| --- | --- | --- | --- |
| `CD8_COGNATE_CONTACT_DEGRANULATION` | contact | CD8 | strict identity; polygon contact; cognate recognition `unobservable_by_design` |
| `MACROPHAGE_PRESENTS_MHCII_TO_CD4` | contact | macrophage | `CD74`; MHC-II itself layer-deleted |
| `APC_CTLA4_COSTIM_WITHDRAWAL` | contact | macrophage, B | C11, fully on panel |
| `MACROPHAGE_EFFEROCYTOSIS` | contact | macrophage | strict identity; target must be engine-created apoptotic |
| `B_FOLLICULAR_POSITIONING` | migration | B | `CXCR5`; C01 |
| `CAF_TUMOR_INTERFACE_MATRIX` | secretion | CAF, fibroblast | tumour interface + matrix transcripts |
| `TUMOR_VEGFA_SECRETION` | secretion | tumour, CAF, macrophage | `VEGFA`; C28 |
| `PLASMA_CELL_SECRETION` | secretion | plasma | lineage-level agreement, not exact |
| `TUMOR_CYCLE_PERMISSIVE` | cycle | tumour | strict identity; displaceable neighbour required |
| `HYPOXIA_ADAPTATION` | stress | most types | off by default; needs the hypoxia perturbation |
| `ENDOTHELIAL_SPROUTING` | differentiation | endothelium | off by default; needs angiogenesis |
| `TREG_SUPPRESSION` | contact | CD4 | off by default; needs a declared Treg identity scenario |

### 13.3 Measured eligibility in the reference patch

Produced by `scripts/build_jev_state.py` with no `--rule`:

| Rule | Eligible cells | Eligible interfaces |
| --- | --- | --- |
| `B_FOLLICULAR_POSITIONING` | 120 | 120 |
| `TUMOR_CYCLE_PERMISSIVE` | 138 | 138 |
| `CAF_TUMOR_INTERFACE_MATRIX` | 57 | 149 |
| `PLASMA_CELL_SECRETION` | 38 | 38 |
| `TUMOR_VEGFA_SECRETION` | 33 | 33 |
| `MACROPHAGE_PRESENTS_MHCII_TO_CD4` | 20 | 23 |
| `APC_CTLA4_COSTIM_WITHDRAWAL` | 17 | 20 |
| `MACROPHAGE_EFFEROCYTOSIS` | 6 | 31 |
| **`CD8_COGNATE_CONTACT_DEGRANULATION`** | **1** | **2** |

Upper bound on Jev calls per tick: **≤ 430** of 1,000 cells, before further gating.

The last row deserves emphasis. In the patch chosen precisely because it maximises CD8–tumour contact, exactly one cell satisfies the strict version of the canonical cytotoxic rule: a CD8 T cell both annotations agree on, touching a tumour cell both annotations agree on. Under the permissive policy it is 29. The simulation can be run either way; it cannot be run without choosing, and the choice must appear in the audit record.

Note also that `MACROPHAGE_EFFEROCYTOSIS` is eligible for 6 cells only because the patch contains no dead cells at all — every apoptotic target is engine-created, so this rule is ineligible at *t* = 0 by construction and becomes live only once the simulation kills something.

---

## 14. Perturbations

Four scenarios ship. **Every one is `SIM`.** Each declares the state variables it adds, the rules it unlocks or modulates, what LUAD3 can and cannot show about it, and a reporting requirement that survives into every figure.

### 14.1 Hypoxia

Adds `field.oxygen`, dimensionless, seeded from distance to the nearest endothelial cell — a measured geometry under a `SIM` mapping. Unlocks `HYPOXIA_ADAPTATION`; modulates the cycle, VEGFA and matrix rules.

Available: nearest-endothelial distance; `GOBP_RESPONSE_TO_OXYGEN_LEVELS` (17 of 350 genes, `low_coverage`); `SLC2A1` (16.9 % in tumour); `VEGFA` (52.0 %).
**Not available: pO₂, perfusion, `CA9`, `EGLN3`, `BNIP3`, `HIF1A`, lactate, pH.**

The field carries no physical units and must never be labelled mmHg or nM. A stained vessel does not establish perfusion. Glycolysis and respiration coexist in human lung tumours [R21], so no universal glycolytic switch may be implemented; and glucose uptake is not a tumour monopoly [R22].

### 14.2 Angiogenesis

Adds `field.vegfa` and `vessel.segment_perfused`. Unlocks `ENDOTHELIAL_SPROUTING`.

Available: `VEGFA` by cell type, `KDR` (23.9 % in endothelium), `PECAM1`, `PLVAP`, endothelial polygons.
Not available: `FLT1`, lumen, perfusion, HEV, lymphatic/blood separation.

Endothelial proliferation does not instantly create a perfused vessel; a sprout extends geometry only, and because the tissue is fully tiled it must displace cells to do so. A run may show geometry changing; it may not report oxygen delivery unless a perfusion model is separately declared.

### 14.3 Treatment-resistance mutation

Adds `scenario.genotype`, `scenario.resistance_mechanism`, `cell.drug_sensitivity`, `scenario.treatment_active`. Modulates the cycle and hypoxia rules.

Available as **expression**: `EGFR` (80.0 % of tumour cells), `MET` (80.2 %), `ERBB2`, `AXL`, `YAP1`, `ZEB1` — the classic bypass and EMT axes.
Not available: `KRAS`, `STK11`, `KEAP1`, `NFE2L2`, any DNA-level variant, treatment history, stage, histology.

**Expression of `EGFR` does not establish an `EGFR` mutation**, and a transcript signature cannot establish `KEAP1` loss. Genotype is a declaration, never an inference; it changes dependencies, not lineage [R25, R32]. Every figure from a resistance run must name the declared genotype and say it was assigned.

### 14.4 Checkpoint blockade

Adds `scenario.checkpoint_axis_declared`, `cell.pd1_state`, `scenario.blockade_efficacy`. Modulates degranulation and costimulation withdrawal.

Available: `CD274` (5.1 % tumour, 7.0 % macrophage), `CTLA4` (17.9 % of CD8), `LAG3` (3.7 %), `TIGIT` (20.1 %).
Not available at usable rates: `PDCD1` (0.6 % of CD8 cells, 0.3 % overall), `PDCD1LG2`, protein-level anything, response.

This axis is entirely declared. And because CD8–tumour contact occurs in 1.38 % of CD8 cells, relieving inhibition changes very few cells: **a blockade run that produces large tumour killing is reporting the migration model, not the checkpoint model.** State the assumed PD-1 prevalence explicitly, since the data supply none.

### 14.5 Inflammation

Adds `field.tnf`, `field.il1b`, `field.il6`, `field.ifng`, plus `scenario.pathogen_enabled` (default false) and `actual_microbial_status: unknown`.

Available as **ligand** transcripts: `TNF`, `IL1B`, `IL6`, `CXCL9`, `CCL22`, `CXCL5`.
Not available: every corresponding receptor, and `IFNG` itself. Nothing in this dataset identifies an IFNγ source.

`IL1B` transcript does not demonstrate mature IL-1β processing and release; TNF must not always trigger apoptosis; LUAD alone establishes no pathogen, and endogenous injury generates DAMPs without infection. Any inflammation run operates under an assumed-competence profile by definition and must be labelled so.

---

## 15. Jev integration

### 15.1 What Jev is

Jev is TypeSafe's first public System One model: a model built for fast structured decisions inside software rather than text generation. It returns type-safe values with calibrated probabilities, is documented at 70–500 ms end-to-end, and exposes three question primitives [T05, T01, T02, T03].

| Primitive | `criteria` | Returns | Semantics here |
| --- | --- | --- | --- |
| `choice` | object mapping option key → description, ≤ 255 options | `choice`, `probabilities`, `confidence` | Which admissible behaviour. `confidence` measures concentration of the distribution, **not** biological correctness |
| `score` | ordered array of 2–10 level descriptions | `score`, `legend`, `probabilities`, `confidence` | Position on an ordered rubric. Never a concentration, never a rate |
| `noul` | optional `{true, false}` | `noul` | P(yes). No separate confidence, because two outcomes are fully described by one number. 0.5 does not mean intermediate biological intensity |

Requests go to `POST https://api.typesafe.ai/v1/systemone` with `model`, `state` (string, object or array) and `questions`. Context is documented at 64k tokens.

### 15.2 What Jev is asked, and what it is never asked

Jev ranks admissible behaviours that code has already validated (constraint H20). It is **never** asked whether a cell dies, whether it divides, what its identity is, or for any rate, concentration or duration. A returned option probability is not an event rate and may not be converted to a per-step hazard without independent calibration (H21).

Question authoring follows the documented rule for Score — *describe situations, not degrees* — so a level reads as a state of the world the model can match, never as "moderately high".

### 15.3 The state projection

**The rulebook never travels.** The engine builds a small `state` per decision:

Always included: cell id; identity candidates and agreement; region with the TLS-maturity caveat attached; detection depth and decile; contacts with partner identity candidates and interface lengths, ordered by interface; the engine's allowed actions; **excluded actions with their reasons**; the decision horizon; the probability semantics; the active assumed-competence profile.

Included when relevant: signature percentiles for the signatures the rule's modulators name, each with its coverage flag; gene detections restricted to the genes the rule names, with spillover flags; the 30 µm neighbourhood, only for a soluble-signalling question; active perturbation fields and their dimensionless values.

**Never included:** a raw UCell value without its percentile and coverage flag; the full 302-gene vector; any `unobservable_by_design` field presented as observed; literature citations, rule text, or the rulebook.

The `excluded_actions_with_reason` block exists so a reviewer can tell an action judged implausible from one never offered. Changing the candidate set changes Choice probabilities even when biological state is identical, so the reason list is what makes that change traceable.

Measured payload sizes for the shipped examples: 917–1,145 tokens against a 700-token target and a 2,000-token cap.

### 15.4 Call policy

Call only for cells whose admissible set has more than one option after eligibility. Quiescent cells retain state and cost nothing. In the reference patch, ≤ 430 of 1,000 cells have any eligible rule; 866 have a heterotypic contact, which is the loose upper bound.

Independent questions for one cell share one request; their answers do not condition on each other, which is why migration and secretion may be batched while two mutually exclusive contact actions may not. At 70–500 ms per request, 1,000 cells at 32-way concurrency is roughly 3–16 s per tick.

An API failure triggers a declared fallback — a deterministic admissible policy or maintenance. It must not silently erase a damage event or freeze the biological clock. Validate that returned probability keys match the submitted options, that values lie in [0,1] and sum to ≈ 1, and record the returned model identifier. `jev-latest` can change; pin a version for any defined experiment.

### 15.5 Audit

Every decision records: cell id, tick, rulebook and calibration versions, patch id, rule id, domain, state hash, model requested and returned, eligible options, excluded options with reasons, selected option, option probabilities, confidence, identity agreement, assumed-competence profile, active perturbations, score-use flags, whether it was applied, engine validation result, random seed.

Runs made under identity conflict, under an assumed-competence profile, or under any perturbation must be reportable separately from a baseline run.

---

## 16. Engine constraints

H01–H12 are the general constraints: dead cells do not act; actions belong to the authorised repertoire; cytotoxicity needs contact, target and recognition; division needs a completed cycle, resources, space and identity; cells and mediators have recorded origins; multicomponent receptors need their mechanism; irreversible death overrides behaviour selection; state changes preserve identity and history; events resolve from a common snapshot; quantities cannot go negative; missing information cannot become an observed fact.

Nine more are forced by measurements in this manual:

| ID | Constraint | Basis |
| --- | --- | --- |
| H13 | A raw UCell value may not appear in any threshold, rate or magnitude. Only a percentile within type and depth decile, or a depth residual, may. | ρ up to 0.81 with depth |
| H14 | A signature flagged `identity_confounded` or `low_coverage` may not be sole evidence for a capability gate. | No signature has both adequate coverage and no confound |
| H15 | Identity conflicts propagate; a conflicted cell acts only in the intersection of its candidate repertoires unless a scenario is declared. | 34.9 % exact, 62.6 % lineage agreement |
| ~~H16~~ | Superseded by H04 once polygons arrived. | — |
| H17 | A rule requiring a `not_assayed` component is ineligible unless an assumed-competence profile is active, and every decision under one is tagged. | 32 of 34 edges incomplete |
| H18 | The tissue is a near-complete tiling. Movement and division displace; they never occupy void. | 6.11 contacts, full perimeter contacted |
| H19 | The 16,591 QC-dropped segmented cells are `occluded_neighbour` agents. | 7.5 % of contacts, 28.2 % of cells, biased by type |
| H20 | Jev is never asked whether a cell dies, divides, or what it is. | design |
| H21 | A Jev option probability is not an event rate. | calibration |

H04 replaces the old contact constraint: **contact is the polygon graph at gap ≤ 1 µm and nothing else.**

---

## 17. Validation

### 17.1 Consistency

No division of dead cells; no CD8 attack without contact and declared recognition; no incompatible lineage transition; no debris consumed twice; no negative resources; unassayed receptors stay unknown; a candidate TLS with insufficient markers stays indeterminate.

Build opposed test cases: the same CD8 state with and without a tumour contact; the same B state with and without help; the same migratory cell on an open and a blocked path. These check the engine, not the biology.

### 17.2 The contact graph is an independent axis

The polygons come from segmentation, not from the annotation or the TLS pipeline, so reproducing the contact structure is a genuine test. Targets: mean contacts per cell 6.11; homotypic enrichment Tumour 4.60, proliferating tumour 21.58, B 4.98, CAF 4.63, CD8 2.99; CAF–tumour interface share 0.208.

### 17.3 Circularity traps

- **Do not validate TLS structure against B-cell enrichment.** The candidate cores *are* the `first_type == B_cell` mask.
- **Do not validate `Tumor_proliferating` against the mitotic score.** The label was defined from cycle genes — and the test fails anyway.
- **Do not validate against the 30 µm neighbourhood**, a derived quantity with no independent standing.

### 17.4 Depth-matched nulls

Before reporting any spatial or regional difference in a signature, repeat the comparison after matching cells on depth decile within cell type. The mature-versus-primary B-cell comparison in §7 shows why: the entire visible difference sits inside a one-gene difference in median depth.

### 17.5 Temporal prediction

A single cross-sectional section supplies no ground-truth next state. Hiding part of the section tests spatial interpolation, not time. Candidate validation systems: viable tumour slices, organotypic culture, repeated live imaging, matched pre/post perturbation material [R18]. Define outcome and horizon *before* calibrating.

### 17.6 Does Jev add anything?

Compare, under matched initial conditions and parameter budgets: a fixed rule-only policy; a fitted statistical policy on the same inputs; the same engine with Jev; and ablations of neighbourhood, signature state and history. For probabilistic predictions use calibration curves and proper scoring rules, and test stability under missing markers, alternative labels and changes to the allowed-action menu.

---

## 18. What remains unknown

| Quantity | Status | What would resolve it |
| --- | --- | --- |
| Cognate antigen recognition | `unobservable_by_design` | V(D)J, antigen-specific assay |
| Cytokine concentrations and secretion rates | unmeasured | protein/secretion assay; most receptors are `not_assayed` |
| pO₂, glucose, lactate, pH, perfusion | unmeasured | physiological imaging |
| Migration, division, death rates | uncalibrated | live slices, repeated imaging |
| Cell ontogeny | unknown | lineage tracing [R07] |
| Genotype, stage, treatment, histology | absent from the object | clinical metadata |
| Cell-death state | not represented | a death marker; dead cells are under-segmented by construction |
| TLS maturity as a per-cell state | label present, no correlate | FDC network, protein, `AICDA`/`BCL6` |
| Contact area in 3-D | unknown | serial sections or 3-D segmentation |
| Jev probability → event rate | not estimated | defined outcomes, horizons, independent calibration |

### 18.1 Priorities

1. **Reconcile the annotations**, or commit explicitly to running on identity distributions. This is now the largest single source of uncertainty, and the polygons make it worse rather than better: a cell's contact partners are as conflicted as the cell itself.
2. **Add a physical matrix channel.** It is the missing mechanism behind both the measured immune exclusion and the CAF sheath around tumour nests.
3. **Resolve the scoring-layer question.** Whether `HLA-A` and `HLA-DPB1` should be read from `raw_counts` is a decision about the SPLIT correction that we cannot make from the delivered object alone.
4. **For a future panel, add receptors, not more ligands:** `IFNGR1/2`, `CSF1R`, `CXCR3`, `CCR2`, `CXCR4`, `IL6ST`, `TGFBR1/2`, `TNFRSF1A/B`, `IL10RA`, `CD40`, `CD28`, `IL21R`, `FAS`, `KLRK1`, plus `B2M`, `TOX`, `AICDA`, `BCL6`, `CR2`. That set alone would move twenty of the thirty-four edges out of `assumed_only`.

---

## 19. Repository contents

```
luad-virtual-tissue/
├── MANUAL.md                              this document
├── README.md                              quick start
├── rulebook/
│   ├── rulebook.json                      the machine-readable rulebook
│   ├── rulebook.schema.json               JSON Schema 2020-12
│   ├── calibration.json                   reference distributions (generated)
│   ├── calibration.schema.json
│   ├── question_templates.json            Jev `questions` blocks
│   └── question_templates.schema.json
├── scripts/
│   ├── build_calibration.py               h5ad -> calibration.json
│   ├── export_patch.py                    h5ad + polygons -> patch JSON
│   ├── build_jev_state.py                 patch + rulebook -> /v1/systemone request
│   ├── validate_bundle.py                 schema + cross-reference checks (CI)
│   ├── derive_reference_tables.py         composition, signatures, neighbourhoods
│   └── derive_true_contacts.py            polygon contact graph and interfaces
├── examples/
│   ├── patch_B26.json                     the reference patch, 1,000 cells
│   └── jev_request_*.json                 three worked requests
└── data/                                  derived tables cited in this manual
```

`python scripts/validate_bundle.py` must exit 0 on every pull request that touches `rulebook/`. It checks the three JSON documents against their schemas and then the cross-references a schema cannot express: that every rule's capability exists and is declared by every identity it lists; that no rule grants a capability its cell type lacks; that question templates and rules point at each other and agree on domain and primitive type; that a perturbation never unlocks an already-enabled rule; that an edge marked `complete` really has nothing missing and the summary count matches; that calibration and rulebook agree on cell types and annotation column; and that versions match across the bundle.

That validator earned its place: it caught seven real inconsistencies on first run, including a rule granting hypoxia adaptation to six cell types that never declared it.

---

## 20. References

### Primary literature

Reference notes state the specific use here and the main transfer limit. "Abstract/record" means the bibliographic record and abstract were examined, not that all figures and supplementary data were audited.

**R01.** Lavin Y et al. (2017). [Innate Immune Landscape in Early Lung Adenocarcinoma by Paired Single-Cell Analyses](https://doi.org/10.1016/j.cell.2017.04.014). *Cell*. PMID 28475900. — H-LUAD. Tumour-associated immune change is present already in early disease; do not reserve it for advanced disease.

**R02.** Lambrechts D et al. (2018). [Phenotype molding of stromal cells in the lung tumor microenvironment](https://doi.org/10.1038/s41591-018-0096-5). *Nature Medicine*. PMID 29988129. — H-NSCLC. Fibroblast and endothelial diversity, including matrix and immune-recruitment programmes. Transcriptional clusters are not measures of perfusion, matrix mechanics or secretion.

**R03.** Guo X et al. (2018). [Global characterization of T cells in non-small-cell lung cancer by single-cell sequencing](https://doi.org/10.1038/s41591-018-0045-3). *Nature Medicine*. PMID 29942094. — H-NSCLC. Exhaustion-associated states and Treg heterogeneity. Cross-sectional structure supplies no transition kinetics.

**R04.** Zilionis R et al. (2019). [Single-Cell Transcriptomics of Human and Mouse Lung Cancers Reveals Conserved Myeloid Populations](https://doi.org/10.1016/j.immuni.2019.03.009). *Immunity*. PMID 30979687. — H-NSCLC, M-LUNG. Supports separating monocytes, macrophages, DCs and neutrophils rather than an M1/M2 axis.

**R05.** Kim N et al. (2020). [Single-cell RNA sequencing demonstrates the molecular and cellular reprogramming of metastatic lung adenocarcinoma](https://doi.org/10.1038/s41467-020-16164-1). *Nature Communications*. PMID 32385277. — H-LUAD. Explicitly notes dissociation bias; site and patient comparisons are not longitudinal.

**R06.** Leader AM et al. (2021). [Single-cell analysis of human non-small cell lung cancer lesions refines tumor classification and patient stratification](https://doi.org/10.1016/j.ccell.2021.10.009). *Cancer Cell*. PMID 34767762. — H-NSCLC. The activation module linking PDCD1⁺CXCL13⁺ T cells, IgG⁺ plasma cells and SPP1⁺ macrophages. Co-occurrence is not a uniform interaction.

**R07.** Casanova-Acebes M et al. (2021). [Tissue-resident macrophages provide a pro-tumorigenic niche to early NSCLC cells](https://doi.org/10.1038/s41586-021-03651-8). *Nature*. PMID 34135508. — H-NSCLC, M-LUNG. Origin-dependent macrophage contributions. Human RNA phenotype alone does not establish ontogeny.

**R08.** Salcher S et al. (2022). [High-resolution single-cell atlas reveals diversity and plasticity of tissue-resident neutrophils in non-small cell lung cancer](https://doi.org/10.1016/j.ccell.2022.10.008). *Cancer Cell*. PMID 36368318. — H-NSCLC. Compositional heterogeneity across 1,283,972 cells; mixed protocols preclude a universal composition.

**R09.** Sikkema L et al. (2023). [An integrated cell atlas of the lung in health and disease](https://doi.org/10.1038/s41591-023-02327-2). *Nature Medicine*. PMID 37291214. — Human lung reference for resident identities. Not a LUAD frequency prior.

**R10.** Dieu-Nosjean MC et al. (2008). [Long-term survival for patients with non-small-cell lung cancer with intratumoral lymphoid structures](https://doi.org/10.1200/jco.2007.15.0284). *JCO*. PMID 18802153. — H-NSCLC. Association of lymphoid organisation with outcome; not a killing probability.

**R11.** de Chaisemartin L et al. (2011). [Characterization of chemokines and adhesion molecules associated with T cell presence in tertiary lymphoid structures in human lung cancer](https://doi.org/10.1158/0008-5472.can-11-0952). *Cancer Research*. PMID 21900403. — H-NSCLC. TLS chemokines, adhesion molecules and PNAd⁺ HEV. Supports recruitment architecture, not fixed concentrations.

**R12.** Germain C et al. (2014). [Presence of B cells in tertiary lymphoid structures is associated with a protective immunity in patients with lung cancer](https://doi.org/10.1164/rccm.201309-1611oc). *AJRCCM*. PMID 24484236. — H-NSCLC. Local B differentiation and humoral responses; specificity cannot be assigned from generic markers.

**R13.** Goc J et al. (2014). [Dendritic cells in tumor-associated tertiary lymphoid structures signal a Th1 cytotoxic immune contexture](https://doi.org/10.1158/0008-5472.can-13-1342). *Cancer Research*. PMID 24366885. — H-NSCLC. Mature DCs and Th1/cytotoxic context. Association, not per-cell causation.

**R14.** Patil NS et al. (2022). [Intratumoral plasma cells predict outcomes to PD-L1 blockade in non-small cell lung cancer](https://doi.org/10.1016/j.ccell.2022.02.002). *Cancer Cell*. PMID 35216676. — H-NSCLC. Plasma-cell signatures and outcome under atezolizumab. Does not establish antibody specificity.

**R15.** Zhan X et al. (2026). [Uncovering ectopic GC-like niches for tumor reactive lymphocyte priming in lung adenocarcinoma using Stereo-XCR-seq](https://doi.org/10.1038/s41467-026-75405-x). *Nature Communications*. PMID 42547508. — H-LUAD. Plasma-cell aggregates forming GC-like niches outside conventional TLS. Directly relevant to the six plasma-dominated candidates in §7; Xenium without V(D)J cannot reproduce the clonal evidence.

**R16.** Ho YH et al. (2026). [Nociceptive innervation limits tertiary lymphoid structures to promote lung cancer](https://doi.org/10.1016/j.cell.2026.04.038). *Cell*. PMID 42161272. — M-LUNG. A CGRP–macrophage–fibroblast circuit limiting TLS. Optional extension, disabled here: `CALCA` is on the panel but no innervation annotation exists.

**R17.** Maier B et al. (2020). [A conserved dendritic-cell regulatory program limits antitumour immunity](https://doi.org/10.1038/s41586-020-2134-y). *Nature*. PMID 32269339. — H-NSCLC, M-LUNG. The mregDC programme; maturation and regulation coexist. Note that `LAMP3` is not DC-specific in LUAD3 (§9.2).

**R18.** Salmon H et al. (2012). [Matrix architecture defines the preferential localization and migration of T cells into the stroma of human lung tumors](https://doi.org/10.1172/jci45817). *JCI*. PMID 22293174. — H-NSCLC. Live human tumour-slice imaging with collagenase perturbation. The mechanism behind §5.1, and the model for §17.5 validation.

**R19.** Simoni Y et al. (2018). [Bystander CD8+ T cells are abundant and phenotypically distinct in human tumour infiltrates](https://doi.org/10.1038/s41586-018-0130-2). *Nature*. PMID 29769722. — Human lung and colorectal tumours. Keeps tumour recognition separate from infiltration and effector markers — the basis for treating cognate recognition as `unobservable_by_design`.

**R20.** Jansen CS et al. (2019). [An intra-tumoral niche maintains and differentiates stem-like CD8 T cells](https://doi.org/10.1038/s41586-019-1836-5). *Nature*. PMID 31827286. — X-TISSUE. APC-associated niches for stem-like CD8 cells. Transferred niche biology, not evidence that every LUAD TLS contains this programme.

**R21.** Hensley CT et al. (2016). [Metabolic Heterogeneity in Human Lung Tumors](https://doi.org/10.1016/j.cell.2015.12.034). *Cell*. PMID 26853473. — H-NSCLC. Intraoperative isotope tracing in nine patients: glucose oxidation alongside glycolysis. Forbids a universal glycolytic switch (§14.1).

**R22.** Reinfeld BI et al. (2021). [Cell-programmed nutrient partitioning in the tumour microenvironment](https://doi.org/10.1038/s41586-021-03442-1). *Nature*. PMID 33828302. — X-TISSUE. Myeloid cells take up more glucose than cancer cells. Rejects an assumed tumour monopoly on glucose.

**R23.** Guo JY et al. (2013). [Autophagy suppresses progression of K-ras-induced lung tumors to oncocytomas and maintains lipid homeostasis](https://doi.org/10.1101/gad.219642.113). *Genes & Development*. PMID 23824538. — M-LUNG. Genotype-dependent autophagy effects; "high autophagy" is not synonymous with death.

**R24.** Wang W et al. (2019). [CD8+ T cells regulate tumour ferroptosis during cancer immunotherapy](https://doi.org/10.1038/s41586-019-1170-y). *Nature*. PMID 31043744. — X-TISSUE. IFNγ-associated changes in cystine transport and tumour ferroptosis. Kept separate from apoptosis; ferroptosis is not enabled here.

**R25.** Skoulidis F et al. (2018). [STK11/LKB1 Mutations and PD-1 Inhibitor Resistance in KRAS-Mutant Lung Adenocarcinoma](https://doi.org/10.1158/2159-8290.cd-18-0099). *Cancer Discovery*. PMID 29773717. — H-LUAD. Genotype as a context variable for §14.3. Not used to assign a genotype to LUAD3.

**R26.** Andreatta M et al. (2021). [UCell: Robust and scalable single-cell gene signature scoring](https://doi.org/10.1016/j.csbj.2021.06.043). *CSBJ*. PMID 34285779. — METHOD. Rank-based scoring semantics.

**R27.** Andreatta M et al. (2026). [UCell and pyUCell: single-cell gene signature scoring for R and Python](https://doi.org/10.1093/bioinformatics/btag055). *Bioinformatics*. PMID 41665985. — METHOD. The implementation used (pyUCell 0.7.3).

**R28.** Troulé K et al. (2025). [CellPhoneDB v5: inferring cell-cell communication from single-cell multiomics data](https://doi.org/10.1038/s41596-024-01137-1). *Nature Protocols*. PMID 40133495. — METHOD. Source for the interaction registry. Database membership is not LUAD functional proof.

**R29.** Browaeys R et al. (2020). [NicheNet: modeling intercellular communication by linking ligands to target genes](https://doi.org/10.1038/s41592-019-0667-5). *Nature Methods*. PMID 31819264. — METHOD. Prediction, not measurement of secretion or receptor occupancy.

**R30.** Dimitrov D et al. (2024). [LIANA+ provides an all-in-one framework for cell-cell communication inference](https://doi.org/10.1038/s41556-024-01469-w). *Nature Cell Biology*. PMID 39223377. — METHOD. Evidence prioritisation, not proof of communication from proximity.

**R31.** Zitti B et al. (2026). [Positioning and reversible suppression of CCR7⁺ dendritic cells in perivascular tumor niches shape cancer immunity](https://doi.org/10.1016/j.immuni.2025.11.020). *Immunity*. PMID 41421339. — Mixed scope. Treg–DC contact reducing costimulation; the basis for encoding C11 as a contact mechanism rather than a diffusible effect.

**R32.** Romero R et al. (2017). [Keap1 loss promotes Kras-driven lung cancer and results in dependence on glutaminolysis](https://doi.org/10.1038/nm.4407). *Nature Medicine*. PMID 28967920. — M-LUNG. NRF2 activation and glutaminolysis dependence. A transcript signature cannot establish `KEAP1` mutation (§14.3).

### Technical sources

**T01.** TypeSafe. [Choice](https://docs.typesafe.ai/primitives/choice). Accessed 22 September 2026. Criteria shape, option limit (255), returned `choice`, `probabilities`, `confidence`.

**T02.** TypeSafe. [Score](https://docs.typesafe.ai/primitives/score). Accessed 22 September 2026. Ordered rubric of 2–10 levels; `score` is the probability-weighted mean level index; "describe situations, not degrees".

**T03.** TypeSafe. [HTTP API reference](https://docs.typesafe.ai/api). Accessed 22 September 2026. `POST /v1/systemone`; `state` may be a string, object or array; `model`; `questions`.

**T04.** TypeSafe. [Noul](https://docs.typesafe.ai/primitives/noul). Accessed 22 September 2026. Binary probability; no separate confidence field, and why.

**T05.** TypeSafe. [Introducing System One models and Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev). Accessed 22 September 2026. System One model class, RLCD training, calibrated structured outputs, 70–500 ms latency, 64k context.

### Data sources

**D01.** LUAD3 delivery, `LUAD3_TLS_GO20_UCell.h5ad`, sha256 `341e6e591e9dd6cd3f617919ac0e0683ebc5632f7879e25d6a9756d611795752`; source object `Xenium_LUAD_No3_annotated.h5ad`. Every `D-LUAD3` value derives from this file.

**D01b.** `cell_boundaries.csv`: 1,950,603 vertices, 150,055 polygons, in the `obsm['spatial']` frame (mean |polygon centroid − `obsm['spatial']`| = 0.72 µm in x, 1.15 µm in y; `spatial_original` is X-mirrored and does **not** match). Source of every contact measurement.

**D02.** MSigDB human 2026.1.Hs, C5:GO:BP, sha256 `ff73a093fc175272f5ccdc424dbf3a6d138810ebfcb8fa90d3b0f13f631f34c0`.

**D03.** pyUCell 0.7.3 — `max_rank=100`, `ties_method='average'`, `missing_genes='skip'`, layer `purified_raw`, no smoothing, CPU.

**D04.** Region assignment `tissue_candidate_assignment.csv`, sha256 `e673be2bffe4d004ae115ce35d37a6e7ddd995162f3d743b51a9490bf474e999`, 28 candidates, 44,134 assigned cells.

---

*Every number in §§2, 4–13 was computed from D01 and D01b by the scripts in this repository and can be regenerated. Where a number describes literature rather than LUAD3, it carries its reference. Where it describes neither, it is labelled `SIM`.*
