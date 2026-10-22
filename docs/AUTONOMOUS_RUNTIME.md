# Autonomous LUAD runtime 0.2.0

**Version 0.2.1 update:** new experiments use `runtime-v2-calibrated.json`. The structural compression constraint, conservative growth initialization and damped recovery of initially hidden cells supersede the corresponding legacy mechanics described below. See [CALIBRATION.md](CALIBRATION.md) and [CALIBRATION_RESULTS.md](CALIBRATION_RESULTS.md). The subsequent live Jev campaign completed 72 h and 17,071 valid individual decisions; see [JEV_CAMPAIGN_5000.md](JEV_CAMPAIGN_5000.md). The historical no-live statements below describe the original v0.2.0 delivery. The campaign runner also supports hidden terminal key input, keeping the key out of the command line and recordings.

Implemented 29 September 2026. B26 is the primary TLS–tumor experiment; B27 is the secondary tumor–stroma comparison. The immutable atlas retains measured polygons, both annotations, raw scores, depth residuals, missing values and contact provenance. The autonomous runtime owns a separate mutable state.

## Entry points and reproducibility

`scripts/run_autonomous.py` records local or explicitly capped Jev experiments. `scripts/verify_autonomous.py` validates completed recordings and writes an aggregate comparison. `scripts/export_player.py` exports a private standalone HTML replay. `server.py` serves both the moving-tissue viewer at `/` and the preserved fixed-geometry laboratory at `/atlas`.

The authority for numerical values, competence assumptions and scenario switches is `contracts/runtime-v2.json`, embedded in every episode. The M1 mechanics exercise remains available through `scripts/run_v2_mechanics.py`; the v0.1 engine and contract remain separate. No sibling runtime code or credentials are imported.

## Initial condition and identity

B26 starts with 1,000 acting cells, including 381 B cells, 205 primary-annotation CD8 cells and 139 tumor cells, plus 441 context objects. B27 starts with 1,000 acting cells and 328 context objects. These are measured initial populations. Born and recruited cells have explicit origins and new, nonreused identifiers.

S0 uses the conservative identity intersection and unknown recognition. S1–S8 use the declared primary annotation policy and explicit recognition. The recognition-off control uses the same primary policy with recognition denied. None of these scenarios infers antigen recognition from RNA, proximity or a pathway score.

The named `autonomous_exploratory_v1` competence profile explicitly assigns functional machinery for the implemented programs, including receptors absent from this panel. Identity and contact gates still apply, and recognition/effector/clearance competence have separate gates. This profile is an experimental model assumption, not a claim that missing receptors or protein states were observed.

B/plasma cells remain quiet mechanical objects. Occluded objects remain unannotated. The outer context ring is fixed; interior context is mechanically active as specified in M1, while its observations and non-autonomous role remain frozen. Context endothelium provides scenario-assigned nutrient exchange but never receives a question, sprouts, recruits or spends resources.

## Fields and mechanics

The existing bounded power diagram supplies cell shapes, pressure, displacements, cell division and removal. Measured polygons are displayed at time zero; later frames reconstruct the recorded power cells. The viewer approximates disk arcs with 48 sides; kernel geometry uses its analytic diagram. Hidden compressed cells remain accounted for and are reported, not silently deleted.

The field grid has 4 µm spacing on a rectangle enclosing the mechanical halo. Its origin and dimensions are identical across scenarios for the same atlas; adding a virtual nerve cannot enlarge the grid. The external nerve's integrated flux is deposited onto the nearest boundary nodes. All fields are SIM dimensionless variables. The boundary otherwise has zero normal flux. Nutrients enter through assigned perfused endothelial sites, not from an arbitrary oxygenated border.

Conservative bilinear deposition transfers integrated cellular sources/sinks onto the grid. For soluble fields, each tick solves `D L c + (decay + sink) c = source`, where `L` is a finite-volume reflecting Laplacian. Nutrient exchange contributes both source and first-order sink; consumption is scaled by target area and the individual glycolytic fraction. Nonnegative sources and sinks produce nonnegative concentrations. Every solve records residual and integrated source/loss balance.

Oxygen and glucose are consumed; glycolysis lowers oxygen demand and raises glucose demand and lactate production. Programs supply IFNγ-like, CXCL9/10-like, VEGF-like and TGFβ-like sources. IFNγ exposure licenses a declared downstream chemokine response in tumor/macrophage cells. Matrix uses conservative implicit Euler integration, so deposition persists after secretion stops and decays over time. Soluble fields are quasi-steady; this approximation does not model molecular transport delay.

The viewer stores every second grid node at 8 µm and five decimal places for display. Physics uses the full grid. Saved positions and final biological states are not rounded. Field colors are dimensionless and use a displayed per-frame range; comparison images may therefore have different color ranges. Compare numeric readouts as well as colors.

## Programs and clocks

| Cell | Implemented behavior and consequence |
|---|---|
| CD8 | Random scan, chemotaxis, hold, disengage, rest, finite-material contact degranulation, exhaustion/recovery and refill; CD4 help licenses a crowding-limited expansion clock |
| Tumor | Space/nutrient-gated accelerated cycle; individual glycolytic/oxidative shifts; IFNγ-gated PD-L1 display; stress-gated VEGF secretion; kernel-owned damage commitment, death and sustained-hypoxia necrosis |
| Macrophage | Contact-bound finite-capacity efferocytosis, patrol, inflammatory chemokine or suppressive VEGF/TGFβ programs with a minimum polarization dwell |
| Endothelial | VEGF-gated tip motion; a new endothelial contact, followed by a delay, is required for perfusion; declared local influx at perfused, chemokine-exposed, uncrowded acting vessels |
| CAF/fibroblast | Tumor-interface matrix or TGFβ deposition; CAF also has a VEGF program |
| CD4 | Chemotaxis and contact help to an already stimulated CD8; help reduces exhaustion and grants a limited division license |
| B/plasma/occluded | No autonomous programs or inference questions |

The tumor cycle is an accelerated 24 h SIM clock. The proliferating annotation initializes a seeded phase offset at the first licensed cycle entry, not an obligatory division. Growth raises target area toward twice its base; division checks local pressure again. Parents keep their IDs; daughters get new IDs and inherited provenance. CD8 division partitions existing pulses instead of duplicating effector material.

Cytotoxic programs require a live contacted acting tumor, declared recognition and competence, material, cooldown completion, adequate glucose and nonterminal exhaustion. Completion rechecks physical contact and target state. Damage is additive and modified by exhaustion, lactate and inhibitory ligand. A threshold commits apoptosis, a separate clock produces intact death, and a macrophage may clear the corpse once. Necrosis requires sustained low oxygen and removes the body with its area recorded. These fates are engine events, never model-selected death options.

Sprouting is a coarse endothelial-tip displacement model. It records a connecting segment; it is not a resolved lumen, vascular tree or hemodynamic model. Existing endothelial neighbors at sprout initiation do not count as a newly formed anastomosis. An unconnected segment does not perfuse. A tip that joins a new perfused endothelial neighbor gains perfusion only after the declared delay. Recruitment is a declared finite per-vessel insertion process followed by tissue relaxation, not measured leukocyte traffic.

## Virtual nerve

No nerve is observed in this patch. S5/S6/S8 place a declared 80 µm line just beyond the tumor-facing halo envelope, outside all initial cell disks. This is an imposed peripheral structure, with an explicit radius and no autonomous identity. NE-like and CGRP-like signals have separate switches. NE can increase exhaustion, reduce motility and license tumor VEGF or a cycle preference; CGRP can increase exhaustion. These transfers are SIM assumptions and their numerical coefficients are not literature-fitted lung parameters.

The line emits a spatial source; it does not imply innervation in this patient. Report any difference only as the **effect of a declared virtual nerve in this model**. S2 is the matched nerve-off comparison for S5/S6; S7 is the matched comparison for S8. Comparing S1 directly with S5 also changes recruitment and is not an isolated nerve ablation.

## Wake scheduling and decision audit

A new relevant heterotypic contact, field threshold crossing, program completion, cycle checkpoint or ROI entry may wake a cell. Wake reasons remain pending until its independent minimum interval and availability permit a decision. There must be at least two distinct legal behaviors; inactive synonyms do not manufacture questions. Each cell has a limit of 24 decisions per modeled day. Quiet cells are not recorded as artificial WAIT decisions.

Menus reuse the shared three-valued identity/condition evaluator. Unknown recognition cannot satisfy a gate. The policy sees local identity candidates, SIM state, fields, up to six contacts, wake reasons and excluded options. It never sees an objective tumor count or requested outcome. All proposals come from a common snapshot; seeded reservations resolve competing use of targets. Timed programs run independently between decisions.

The local policy is an explicit state-aware priority controller, not an inferred cellular policy. It prefers clearance/help, licensed killing, migration, context-appropriate metabolism/cycle and alternating stromal secretion. Its one-hot probabilities are bookkeeping. Tumor clearance or progression in a local run is conditional on that controller as well as the contract.

## Jev protocol and replay

The optional adapter batches at most 20 independent questions and at most 40,000 payload bytes (a conservative byte proxy, not an exact token count). A full local dry run estimates actual batches before a live command proceeds. The pinned default model is `jev-1.13.0`; it was not revalidated by a live call in this release.

Validation is per question: keys, finite probabilities/confidence, legal choice, rounded sum tolerance and argmax agreement. A small argmax gap of at most 0.02 may be repaired and is logged with the raw response; larger gaps withhold that cell's program. A transport failure invalidates that batch without retry. Valid peers can proceed, and previously committed clocks continue.

A journal writes and flushes an intent before transport and the result before applying answers. Resume reconstructs from time zero with the same atlas/contract/scenario/seed and reuses exact request hashes. An intent without a result is an uncertain paid call and is never repaid automatically. The cap includes failures and all journaled requests. Interrupted/malformed journals fail closed for review. Keys come only from the process environment and are redacted before response data can enter journals or episodes.

Episodes contain the contract, atlas fingerprint, cell origins, frames, local decisions, all events, provider audit, final state and fingerprints. The verifier checks the final frame's exact IDs, positions and viability against that final state. The portable player verifies a checksum of its embedded compressed payload. Playback only renders recorded states and never calls inference or the simulation kernel.

## Limits and acceptance

Paid recording journals also bind exact Python source hashes. A changed implementation cannot silently reuse the same journal as though only the seed and parameters defined the experiment. After 100 recorded decisions, a paid run stops for review if one cell type exceeds half of decisions or invalid answers exceed 10%.

The model remains uncalibrated. Its confinement wall, missing segmentation objects, power-cell shape approximation, mechanical pressure/motility coupling, accelerated proliferation, competence assignments and source strengths can dominate outcomes. Report hidden cells, crowding, perfusion and decision distribution alongside tumor counts. A 50% perfusion reduction does not guarantee hypoxia; do not tune a scenario merely to obtain a desired phenotype.

The viewer's **Zero-area bodies** readout counts compressed modeled bodies that remain present but have no power-cell area. This is a geometry diagnostic, not a death count. The completed campaign and its substantial compression in some runs are documented in [RESULTS.md](RESULTS.md).

No antigen processing/presentation, clonal identity, GC, somatic hypermutation, class switching, full humoral response, Treg program, resolved lymph/blood flow or patient treatment prediction is implemented. Exhaustion labels are SIM threshold states, not identification of measured TPEX or terminal subtypes. The initial tumor-footprint depth readout refers to the original measured nest footprint, not a reconstructed biological invasion front.

M0 live smoke testing, M5 paid pilots and M6 paid recording campaigns are distinct from software completion. They require explicit paid intent and a cap. A >50% question share in one cell type is a pilot-review flag. Local tests and free trajectories cannot establish Jev response validity, biological calibration or patient-level predictive accuracy.
