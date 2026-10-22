# Operational corrections to the supplied specification

The supplied `MANUAL.md`, `rulebook/rulebook.json`, schemas, templates and calibration remain unchanged. Runtime version `luad-runtime-0.1.0` lives in `contracts/runtime-v1.json`; executable interpretation lives in `src/luad_tissue/conditions.py`. A passing reference schema check does not imply complete executable eligibility.

| Reference behavior or ambiguity | Operational resolution |
|---|---|
| The exploratory `eligible_for()` skips several required conditions | Evaluate all `all` conditions, reject unsupported operators/group structures, preserve unknown and report the reason. The historical helper is not used by the runtime. |
| Plasma identity uses `in`, while the historical helper only checks `eq` | Implement `in`; 19 of the 38 historical candidates have conflicting annotations and fail this condition. |
| Strict cytotoxic identity accepts the T lineage | Require CD8-compatible candidate labels, or an explicit primary-annotation scenario. Cell 95048 is CD8/CD4, not concordant CD8. Under the conservative policy there is no executable CD8–tumor pair. |
| Unknown candidate lineages may be discarded | Retain them as a failed identity intersection. |
| Broad lineage agreement can incorrectly grant subtype capability | Require an accepted primary identity. A primary B cell does not become a plasma cell; a broad secondary B label can support an already primary-labeled plasma cell. Broad secondary Myeloid supports a primary macrophage; secondary DC does not establish macrophage competence. |
| H15 versus permissive reversible rules | The current runtime uses conservative capability intersections by default. The alternative `primary_annotation` is an explicitly disclosed scenario, not a silent exception. |
| Historical report sums to 430 | This is 430 cell–rule matches, 390 distinct cells, before full gate resolution. It is not an executable-cell or request count. |
| Historical eferocytosis opportunities include living targets | Require an engine-created apoptotic/dead target, current contact and available finite processing capacity. |
| Templates copy menus before all prerequisites are resolved | Build per-target menus from executable handlers; reference templates are never submitted wholesale. Shared APC templates do not jointly authorize distinct mechanisms. |
| API example claims eligibility while recognition is unresolved | The live adapter only receives runtime-authorized choices. The historical examples explicitly disable quantitative execution and remain reference material. |
| Raw scores versus type/depth calibration | Raw values and within-type percentiles are descriptive. Preserve the original within-type zero-percentile convention. Compute depth residuals against the frozen type × raw-count-QC depth-decile medians. No current handler consumes a signature as a gate or magnitude. |
| Six reference signature flags default to `sufficient` | Preserve `reference_coverage_flag`, but assign operational `low_coverage`; retain `identity_confounded` for the other six relevant signatures. Do not rewrite the frozen calibration. |
| Missing scores | Preserve the 17 unscored B26 cells and 305 unscored B27 cells without imputation or zero filling. |
| MHC transcripts versus actual presentation | Presentation requires additional declared protein/display competence and an implemented handler. Current runtime withholds it. |
| Global core direction in migration templates | No migration handler is implemented. Future navigation must use a declared local field, not omniscient core coordinates. |
| Failure handling differs between LUAD and LN | A failed round commits no new programs, keeps response/request receipts and advances already committed clocks. A budget refusal stops before the round and retains pending state. No automatic retry or hidden provider substitution. |

Measured initialization and simulation assumptions remain separate. Frozen-context cells never choose or receive dynamic damage, and unannotated polygons never acquire a repertoire. The current engine permits clearance of a qualifying intact apoptotic or dead ROI target, as specified by the reference rule. It does not model further digestion, recycling, antigen presentation after uptake, or renewed macrophage capacity.

All deployed handler gates, scheduler availability and action receipts are inspectable. An unavailable handler is a blocker even when reference-level molecular conditions are satisfied.

## v0.2 operational decisions (runtime `luad-runtime-0.2.0.dev1`, milestone M1)

`contracts/runtime-v2.json` is separate from `runtime-v1.json`, which is unchanged. These rows record where M1 departs from, or makes concrete, `docs/PLAN_B26_AUTONOMOUS.md` §3.1 and the MANUAL constraints.

| Plan text or constraint | Operational resolution in M1 | Evidence |
|---|---|---|
| "T-cell migration uses neighbour swaps" (§3.1) | Default motility is a self-propelled site in the packed power diagram, with interface-weighted permeability and substrate traction. Neighbour exchanges emerge as topological changes. `swap` remains selectable. | 72 h B26: swaps moved passive bodies 36–58 µm (endothelium 49 µm), hid 429 bodies and raised mean pressure to 0.45. Self-propulsion moved them 2–7 µm and hid 14. |
| Site of a measured cell | Centroid of the measured polygon, not `obsm/spatial`. The measured coordinate stays in the atlas. | Maximises t=0 overlap with the polygon. |
| Target area | Fitted t=0 simulated area, so t=0 is a declared equilibrium. The measured area is kept for reporting. | Fit 0.9997–1.0003 (5th–95th percentile); the static control is exactly static for 72 h. |
| H04 after t=0 | The same definition (gap ≤ 1 µm) is applied to simulated cells. | Simulated-only graph at t=0: F1 0.905. |
| Contact continuity at t=0 | Handover rule: a t=0 pair keeps its measured status while its site distance stays within 1 µm of t=0. Provenance is recorded per pair. | Without the rule, 7 of the 19 measured CD8–tumour contacts would vanish at the first tick with no cell moving. |
| "Adhesion by type pair" | Not implemented. Pressure is one-sided (no cohesion). Class-specific permeability and viscoelastic matrix anchoring stand in for it. | Adhesion forces would break the t=0 equilibrium without a fitted reference. |
| H18 "never occupy void" | Division and motion always displace neighbours. Compressed boundary cells can expand into measured voids, and this is reported as covered area. | +15 % covered area in the 72 h exercise. |
| Halo "mechanically active; outermost ring fixed" | Fixed if a context body's t=0 site is beyond roi_radius + halo − 12 µm. A wall at that radius confines mobile sites and confinements are counted. | 184 fixed bodies in B26. |
| Division geometry | The parent keeps its identity and one daughter is born (accounting: initial + born + recruited). Axis: long side of the simulated cell's minimum rotated rectangle. | — |
| Cycle entry with one legal option | Not queried. The menu is offered only when the crowding gate is open. | Plan §4: a cell needs ≥ 2 legal options to be queried. |
| Runtime environment | Tested on Python 3.12.14 with `requirements.lock` in a Linux VM. Not yet re-run in the Windows `.venv`. | — |


## Autonomous completion (29 September 2026)

The supplied manual, rulebook and calibration remain reference artifacts. Runtime v0.2 extends the operational contract with a named `autonomous_exploratory_v1` competence profile. It explicitly assigns the machinery for gated programs; it does not convert a missing assay measurement into positive evidence. Recognition and effector/clearance competence still require their own scenario declarations. All new field values and kinetic coefficients are SIM assumptions.

- **H20/H21 and program initiation:** the provider may start a licensed cycle or program. The kernel owns its duration, crowding check, material use, completion, division and death. Choice probabilities never become rates. B/plasma and context cells receive no autonomous questions.
- **Fields:** a reflecting rectangle enclosing the halo replaces the planned tissue-shaped PDE boundary. The solver has 4 µm cells, conservative source deposition and logged mass balance. Matrix is transient implicit Euler; soluble fields are quasi-steady. The viewer samples an 8 µm grid for display only.
- **Identity/geometry:** the M1 interior context remains mechanically active while its observations and repertoire stay frozen. Only the outer ring is position-fixed. t=0 contact uses the measured handover graph; later contact provenance is explicit. The main original atlas remains available and is not overwritten by a trajectory.
- **Nerve placement:** the declared line is just beyond the tumor-facing halo envelope and outside all initial cell disks, rather than drawn through occupied tissue. Its radius and NE/CGRP effects are explicit. It is neither an observed structure nor a cell or decision maker.
- **Matched field domain:** an early development version enlarged the PDE rectangle to include the nerve. That changed nutrient boundary conditions as well as the intended nerve signal. The corrected runtime fixes the same halo-derived grid across every scenario and deposits external nerve flux onto its boundary nodes. All five nerve runs in the final campaign were repeated. Superseded private recordings are retained separately and excluded from the comparison. The completed-run verifier checks equal grid geometry and initial oxygen in the matched controls.
- **Angiogenesis:** a coarse migrating endothelial tip and recorded connecting segment replace a resolved vessel network. Only a newly acquired endothelial contact can establish anastomosis; a separate delay precedes perfusion. Segment geometry alone supplies no oxygen. This is not a lumen or flow solver.
- **Cycle phase and finite material:** the proliferating annotation initializes a seeded accelerated phase offset at licensed entry. CD8 divisions partition finite pulses instead of duplicating them. Recruitment is a finite declared influx at eligible acting vessels, followed by relaxation.
- **Response handling:** v0.2 validates each independent question in a capped batch. Small rounding/argmax repairs are explicitly audited. A durable intent precedes transport; known or uncertain paid requests are not repeated on reconstruction. v0.1's original protocol remains unchanged.
- **Replay ordering:** a frame represents the end of its previous integration interval. Decisions at that same timestamp belong to the following interval and are not shown as already applied. Initial replay has no decision/event history. Exact final positions and viability are checked against the saved full final state.

See `AUTONOMOUS_RUNTIME.md` for the complete executable scope. None of these operational assumptions estimates patient kinetics or establishes biological calibration.

## Structural calibration, runtime 0.2.1

The new `runtime-v2-calibrated.json` preserves the original contracts. It derives type-level area-floor proxies from the measured B26 nucleus/cell area ratios, with explicit sensitivity factors and B27 reserved from parameter derivation. These are lower bounds on 2D simulated geometry, not measured stiffness or individual nuclear boundaries.

The dynamic weight-inflation rescue is replaced by local displacement backtracking and explicit growth, division and influx feasibility checks. Initial growth no longer jumps to an unobserved random cycle phase. A separate damped initialization fit recovers initially hidden B27 cells without moving their measured sites. Biological fates and all IDs remain explicit; no cell is deleted to make a crowded configuration fit. Detailed interpretation, observed limitations and the bounded Jev campaign are in `CALIBRATION.md` and `CALIBRATION_RESULTS.md`.
