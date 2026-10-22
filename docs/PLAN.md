# LUAD3 implementation plan

Accepted on 23 September 2026. This English plan replaces the planning note originally written in Portuguese. The long-term objective is an individual-cell simulation initialized from the real B26 Xenium patch, with B27 as a tumor–stroma comparison from the same specimen.

## Scientific question

How do observed lymphoid–tumor–stromal contacts constrain local responses, and what changes when recognition, inhibitory signaling, movement and remodeling are introduced as explicit assumptions?

The initialization is measured. Future trajectories and kinetic parameters are not measured. Neither region is an independent patient replicate. B26 was deliberately selected for a follicle–tumor interface and cannot represent an unbiased sample of LUAD.

## Ordered milestones

| Milestone | Deliverable | Current status |
|---|---|---|
| A | Reconstructed B26 polygons, frozen halo, dual annotations, 20 signature maps, full-condition audit | Implemented; B27 also reconstructed |
| B | Fixed-geometry contact → damage → death → macrophage clearance, with declared recognition and finite resources | Implemented with local-policy controls |
| C | Optional Jev adapter, decision receipts, bounded recording, saved-state replay | Implemented and tested with synthetic responses; no live Jev run performed |
| D | Deformable mechanics, displacement, CD8 migration, matrix remodeling and tumor cycling | Not implemented; requires mechanical benchmark and new migration rule |
| E | Lymphoid presentation/co-stimulation and secretion programs; B27 comparison | B27 atlas and contact-circuit comparison implemented; additional biological handlers remain withheld |
| F | Checkpoint, hypoxia, VEGFA, angiogenesis, inflammation and resistance studies | Checkpoint has an explicit toy damage multiplier; other perturbations remain withheld |

All populations exist from milestone A, including those without implemented active programs. Inactivity must distinguish missing evidence, absent stimulation and an unavailable handler.

## Architectural decisions

Use an independent Python kernel and a local browser interface. Keep measured observations immutable. A versioned operational contract resolves inconsistencies in the supplied reference without rewriting it. The motor owns physical geometry, event ordering, finite resources, damage and terminal outcomes. A decision provider receives one cell's local observation and an already authorized menu.

Borrow architectural lessons from VirtualTissue and the reactive LN extension: sparse local activation, timed programs, common-snapshot decisions, target reservation, complete provenance and offline replay. Do not import their artificial geometry, open motility corridors, contact radii, kinetics or credentials. Their GC mechanisms are not enabled by B26's primary-follicle annotation.

The request budget is a ceiling, not an experimental objective. Stop at the declared biological horizon. Do not extend persistent secretion merely to consume an inference allowance. Model probabilities never become measured hazards or secretion rates.

## Spatial reconstruction

Select the 1,000 annotated cells nearest the candidate-core centroid. Preserve exact segmentation coordinates. Include a frozen halo covering at least the 30 µm soluble-signaling neighborhood and all contact partners. Retain QC-excluded polygons as physical objects without invented identity. Maintain ROI and context counts separately.

The first runtime has fixed geometry and blocks actions affecting frozen boundary cells. Dynamic experiments will need an extended active domain, explicit boundary fluxes and sensitivity to halo width. Contact after motion must be recomputed from simulated polygons and distinguished from the observed contact graph.

## Operational corrections

Evaluate every declared condition with true/false/unknown outcomes; authorize each action and target separately. Identity agreement at lineage level does not establish CD8 competence. An unknown candidate label cannot be dropped from an intersection. Reconcile the plasma-cell `in` condition, resource checks, cognate recognition and handler availability. Details and original examples are recorded in CONTRACT_CORRECTIONS.md.

Use depth residuals only as contextual covariates. Raw scores remain descriptive. Within-type percentiles are not depth-adjusted. No signature alone establishes a capability. Missing scores stay missing. Preserve provenance for layer-sensitive genes and do not equate RNA detection with functional protein.

## Planned comparisons

Keep initial geometry, seed and horizon matched when comparing: baseline versus declared recognition; recognition off versus on; assigned checkpoint inhibition versus assigned blockade; fixed geometry versus mobility; conservative identity versus a named primary-annotation scenario; B26 versus B27; local policy versus Jev; and ablations of signatures, neighborhood and history.

Report contact creation and duration, permitted/withheld/completed actions, damage, commitment to death, completed death, removal, tumor area, displacement, ancestry and resource conservation separately. Use matched cell-type/depth comparisons for signature analysis. Do not validate B-cell enrichment against a core defined using B cells, or a proliferation label against the same genes used to assign it.

Independent temporal validation requires an appropriate time-resolved experimental system. Cross-sectional reconstruction fidelity is not a validation of dynamics.

## Next milestone

Before milestone D, benchmark deformable-polygon mechanics on an occupied tissue patch. Verify no crossings, overlap creation, disappearance or hidden geometry replacement. Compare integration steps and halo widths. Only then add a CD8 migration contract and finite tumor growth/cycle mechanisms. Keep numerical assumptions versioned and distinguish physical uncertainty from provider-policy uncertainty.
