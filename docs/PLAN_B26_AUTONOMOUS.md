# B26 autonomous-cell runtime (luad-runtime-0.2) — implementation plan

**30 September update:** the explicitly authorized Jev campaign is completed and audited in [JEV_CAMPAIGN_5000.md](JEV_CAMPAIGN_5000.md). Earlier authorization/budget statements below preserve the historical 29 September record.

Drafted 25 September 2026 for hand-off to an implementing model. Builds on
`luad-runtime-0.1.0` (fixed geometry, two handlers) without breaking it.
Read with `MANUAL.md` (constraints H01–H21), `docs/PLAN.md`,
`docs/IMPLEMENTATION.md`, `docs/CONTRACT_CORRECTIONS.md` and `AGENTS.md`.

## Status (25 September 2026)

**29 September implementation update:** M2 fields, M3 autonomous programs, M4 wake scheduling/batched provider/journal, and M7 viewer/export have been implemented. M0 has now returned 20 valid answers in one live request. Version 0.2.1 adds measured structural compression constraints, long local controls and a whole-campaign cap of 1,500 requests. M5/M6 await authorization for the external cellular-data payload following an automatic approval-review rejection. See [CALIBRATION.md](CALIBRATION.md) and [CALIBRATION_RESULTS.md](CALIBRATION_RESULTS.md) for current evidence; [AUTONOMOUS_RUNTIME.md](AUTONOMOUS_RUNTIME.md) and [VERIFICATION.md](VERIFICATION.md) preserve the original implementation. The entries below are the historical M1 hand-off state.

- **M0 (live smoke test): not run.** `api.typesafe.ai` is blocked by the network policy in both the cloud sandbox and the local VM. Run it from the host (Windows) shell with `TYPESAFE_API_KEY` set only in that shell.
- **M1 (geometry + mechanics, LocalPolicy): done** — `src/luad_tissue/v2/`, `contracts/runtime-v2.json` (`luad-runtime-0.2.0.dev1`), `scripts/run_v2_mechanics.py`, tests `tests/test_v2_*.py`. Results and limitations: `docs/IMPLEMENTATION.md` (M1 section). Deviations from §3.1 (self-propelled motility instead of swaps, contact handover rule, one-sided pressure with viscoelastic anchoring, wall at the fixed ring): `docs/CONTRACT_CORRECTIONS.md` (v0.2 section).
- **Historical next step: M2 (fields).** Implemented in the 29 September update, with the static control and v0.1 regression retained.

## 0. Goal

Every live ROI cell of patch B26 (1,000 measured cells, 441 context objects)
acts independently. Jev chooses among kernel-validated behaviours; the kernel
owns physics, clocks, fields, damage, division and death. Nothing scripts the
outcome. Then we observe:

1. Does the tumour compartment grow, stall or shrink?
2. Do CD8 cells migrate to the tumour, kill, and contain it — or become exhausted?
3. What do hypoxia, angiogenesis and glycolytic (Warburg-like) shifts change?
4. What does a declared nerve input change?

Every answer is a property of an **uncalibrated, declared model initialised
from measured geometry** — never a prediction for this patient.

## 1. What already exists (do not rebuild)

| Component | State | Reuse |
|---|---|---|
| `atlas.py`, `outputs/atlas_B26.json.gz` | Exact polygons, both annotations, 20 signatures, contacts, 30 µm halo, occluded objects | Initial condition |
| `conditions.py` | true/false/unknown gate evaluator, identity policies | Keep for gating every menu option |
| `engine.py` | Fixed-geometry CD8 damage → apoptosis → macrophage clearance; common snapshot, target reservation, invariants | Port semantics into v0.2; keep v0.1 runnable and its tests green |
| `providers.py` | Jev adapter, **one cell per request**, never run live | Replace by batched adapter (§6) |
| `server.py`, `web/` | Local studio, replay of fixed polygons | Extend for moving geometry and fields |
| LN repo `jev.py` | Batched (≤20 questions/request), lossless tables, rounding-tolerant validation, audit journal, resume without re-paying | Port the *lessons*, not the code (AGENTS.md forbids importing sibling runtime files) |

Lessons from the LN live runs that must shape v0.2:
- 447 calls carried 8,463 decisions (~19/call) for ≈US$0.60; batching is what makes a 100-call pilot meaningful.
- An HTTP 400 hit the largest batch → keep each request ≤ ~12k tokens and store HTTP error bodies.
- Jev sometimes returns probabilities rounded to 2 decimals (sum ≠ 1) and once returned a `choice` that was not the argmax (0.42 vs 0.43). Handle **per question**, not per batch (§6).
- In the 5,000-call LN run only five cells were ever queried and most calls were one plasma cell choosing SECRETE. v0.2 needs wake conditions and per-cell decision caps so the budget is spread over the tissue.

## 2. Hard facts from B26 that constrain the design

Measured on `atlas_B26.json.gz` (centroid distances; contacts from polygons):

- Composition: B 381, CD8 205, Tumor_proliferating 126, Tumor 13, Fibroblast 70, CD4 59, Macrophage 47, Endothelial 40, Plasma 40, CAF 19. Halo adds 57 CD8, 55 tumour, 28 endothelial.
- Tumour sits at the ROI periphery (97–135 µm from the ROI centre, radius 164 µm). Growth pushes into the halo → the mechanical domain must include the halo.
- CD8 → nearest tumour: 10th/50th/90th percentile 18 / 43 / 70 µm; 25 CD8 within 20 µm, 127 within 50 µm. Only 19 CD8–tumour contacts at t=0. **Migration of a few cell diameters decides everything**; killing without motility is the v0.1 result.
- Tumour → nearest endothelium: quartiles 30 / 41 / 53 µm, max 90 µm. With typical O2 penetration of ~100–150 µm, the *unperturbed* patch should be almost fully oxygenated. Hypoxia will appear only if (a) vessels are declared partly non-perfused, or (b) the tumour grows away from vessels. Report this; do not tune it away.
- Exhaustion cannot be read from data: `TOX`, `HAVCR2` not on panel; `PDCD1` in 0.65 % of CD8; `TIGIT` 20 %, `CTLA4` 18 %, `LAG3` 3.7 %. Exhaustion is a **SIM state variable**, initialised uniformly (optional scenario: seed from TIGIT/CTLA4 detection, labelled as such).
- Glycolysis: `SLC2A1` in 16.9 % of tumour; no `LDHA`, `CA9`, `HIF1A`, lactate, pH. MANUAL §14.1 forbids a universal glycolytic switch (Hensley 2016) → per-cell continuous glycolytic fraction chosen through behaviour, not a global switch.
- **There are no nerves in B26 or in the 302-gene panel** (no S100B, PLP1, MPZ, NGFR, TH, SCN7A, NRXN1, GAP43, UCHL1). `CALCA` is at noise level (~2 %). Any nerve is a declared virtual structure (§5.8) and every nerve result must say so.
- Measured contact at t=0 is the polygon graph (gap ≤1 µm, H04). After t=0 contacts come from simulated geometry and must be labelled `simulated_contact`.

## 3. Architecture

```
atlas_B26 (immutable) ──► TissueState v2 (mutable)
                              │
      ┌───────────────────────┼─────────────────────────┐
  Mechanics             Fields (PDE)              Programs & clocks
  power-diagram cells   O2, glucose, lactate,     per-type state machines,
  forces + T-cell swaps VEGF, CXCL9/10, IFNγ,     damage, exhaustion, cycle,
  division/removal      TGFβ, NE, CGRP            necrosis, sprouting
      └───────────────────────┼─────────────────────────┘
                     Wake scheduler ──► menus (gated by conditions.py + handlers)
                              │
                 Provider: LocalPolicy | Jev batched (≤20 q/request)
                              │
                 Common-snapshot arbitration ──► events ──► episode v2 / replay
```

New package modules under `src/luad_tissue/v2/`: `geometry.py`, `mechanics.py`,
`fields.py`, `programs.py`, `scheduler.py`, `menus.py`, `provider_jev.py`,
`episode.py`. New contract `contracts/runtime-v2.json` (version
`luad-runtime-0.2.0`). v0.1 code and contract remain untouched.

### 3.1 Geometry and mechanics (Milestone D of PLAN.md)

Recommended: **centre-based cells with a power (Laguerre) diagram**.
- Each cell = site (x, y) + target area (measured polygon area) + stiffness class. Geometry each step = power diagram of the sites with weights from target area, clipped to the tissue and to a max radius (so cells at free edges stay round).
- Initial fidelity test: median IoU(measured polygon, t=0 power cell) reported per type; t=0 contact graph compared with the measured graph (F1). The measured polygons are shown at t=0; simulated cells thereafter, never mixed silently.
- Motion: overdamped `v = F/γ` with pressure from area deviation, adhesion by type pair, active motility for CD8 (and macrophage), matrix drag from the matrix field. Substep ≤1 min inside the 10-min tick.
- Packed tissue (H18): T-cell migration uses **neighbour swaps** on the contact graph (a CD8 exchanges position with a neighbour; cost by neighbour class: B/T low, fibroblast medium, tumour nest and CAF/matrix high). This moves lymphocytes through a fully tiled tissue without creating voids.
- Division: daughter site inserted along the long axis; local relaxation; division blocked if local pressure > threshold (records `division_blocked_crowding`).
- Removal: cleared or necrotic cells leave; neighbours relax into the space.
- Domain: ROI + halo are mechanically active; the outermost halo ring is a fixed boundary. Only ROI cells (and their daughters, and newly recruited cells) make decisions. Cells crossing the ROI boundary are tracked, not deleted.
- Invariants: no overlapping power cells; area conservation within tolerance; every cell accounted for (alive + apoptotic + dead + cleared + necrotic + exited = initial + born + recruited).

### 3.2 Fields

2D grid, 2 µm (or 4 µm if slow), dimensionless, quasi-steady solve each tick (`scipy.sparse` reaction–diffusion), boundary = halo edge with declared Dirichlet/Neumann conditions. All values `SIM`, never mmHg or nM.

| Field | Sources | Sinks / effects |
|---|---|---|
| O2 | perfused endothelial cells | consumption by all cells, scaled by (1 − glycolytic fraction); hypoxia and necrosis clocks |
| glucose | perfused endothelium | uptake scaled by glycolytic fraction; CD8 effector function needs glucose |
| lactate | glycolytic cells | suppresses CD8 motility/degranulation, adds to exhaustion; biases macrophages to suppressive |
| VEGF-A | hypoxic tumour, CAF, suppressive macrophage | endothelial sprouting |
| CXCL9/10-like | IFNγ-exposed macrophage and tumour | CD8 chemotaxis |
| IFNγ | engaged/killing CD8 | induces CXCL9/10 and PD-L1 on tumour/macrophage |
| TGFβ | CAF, suppressive macrophage | matrix deposition, CD8 exhaustion/drag |
| matrix | CAF, fibroblast | motility drag, swap cost |
| NE (noradrenaline-like), CGRP-like | virtual nerve only (§5.8) | declared effects on CD8, tumour, endothelium |

## 4. Time and budget

- Tick 10 min; mechanics substeps ≤1 min; fields once per tick.
- Decision intervals (minimum, while awake): CD8 60 min (30 min when in tumour contact), macrophage 180 min, tumour 12 h or at each cycle checkpoint, endothelial 6 h, CAF/fibroblast 12 h, CD4 3 h. B and plasma cells: quiet unless a field or contact wakes them (no questions by default).
- **Wake conditions** (the only way a cell is queried): new heterotypic contact with tumour/CD8/apoptotic cell; field crossing a declared threshold; program completion; cycle checkpoint; entry into the ROI. Quiet cells get no question and no synthetic WAIT. A cell must have ≥2 legal options to be queried.
- Per-cell decision cap per modeled day (default 24) to prevent the LN failure mode.
- Horizon: default 72 modeled hours; extended scenario 7 days. Tumour cycle defaults to an **accelerated 24 h clock**, explicitly labelled (real LUAD doubles in weeks to months).

Budget estimate (to be replaced by the dry-run estimator, §6):
questions ≈ Σ awake cells × horizon / interval. For 72 h: CD8 ~100 × 72 + tumour ~250 × 6 + macrophage 47 × 24 + endothelial 40 × 12 + stroma 90 × 6 ≈ 10.5k questions ≈ **~530 calls** at 20 questions/call (~5–6k input tokens per call measured for 20 B26 questions). The 100-call pilot ≈ 2,000 questions ≈ 12–14 modeled hours.

## 5. Cell programs (all numbers SIM; literature anchors to be verified by the implementer)

Jev never decides death, division outcome, identity, rates or durations (H20, H21). It chooses to *start a licensed program*; the kernel decides whether and when it completes. Record this reading of H20 in `CONTRACT_CORRECTIONS.md`.

### 5.1 CD8 T cell
State: `motility_mode`, `exhaustion_index` e ∈ [0,1], `exhaustion_state` ∈ {effector, progenitor_exhausted (TPEX-like), terminal_exhausted}, `pulses_remaining` (refills slowly while effector), `cooldown`, `engaged_target`, `divisions_left` (after stimulation).
- Menu, free: MIGRATE_UP_CXCL9, SCAN_RANDOM, HOLD_POSITION, REST.
- Menu, in tumour contact: DEGRANULATE:target, HOLD_CONTACT, DISENGAGE, REST.
- Menu, after strong stimulation with help (CD4/IL-2-like contact) and `divisions_left>0`: PROLIFERATE (kernel: 8–12 h cycle, space check).
- Exhaustion accumulation per hour: engaged-with-recognition + PD-L1 on target + lactate + TGFβ + NE/CGRP (nerve scenario); slow decay while resting away from antigen; blockade scenario scales the PD-L1 term down. Thresholds: e ≥ 0.4 → progenitor_exhausted (fewer pulses, still migrates, can proliferate), e ≥ 0.8 → terminal (no pulses, low motility, no proliferation). Both thresholds are declared, not measured.
- Kill: keep v0.1 additive damage (threshold 2 AU; pulse 1 AU × modifiers for exhaustion, lactate, checkpoint). Recognition remains a scenario declaration.
- Anchors to check: CD8 speed in tumours ~2–10 µm/min; additive multi-hit killing (Weigelin 2021); exhaustion under chronic antigen (Guo 2018 in NSCLC; R03).

### 5.2 Tumour cell
State: `cycle_phase` (G0/G1/S-G2-M clock), `glycolytic_fraction` g ∈ [0,1], `pdl1_level`, `hypoxia_clock`, `damage_au`.
- Menu: ENTER_CYCLE (only if O2 and glucose above threshold, space available, not damaged), REMAIN_QUIESCENT, UPREGULATE_PDL1 (only if IFNγ > threshold), SECRETE_VEGFA (only if O2 below threshold), GLYCOLYTIC_SHIFT / OXIDATIVE_SHIFT (step g by ±0.25).
- Kernel: cycle 24 h (accelerated), division needs space; necrosis if O2 < necrosis threshold for > declared time (kernel event, not a choice); apoptosis from CD8 damage as in v0.1.
- Warburg: g raises glucose uptake and lactate output and lowers O2 use. No global switch; heterogeneity is emergent from per-cell choices.

### 5.3 Macrophage (SPP1)
- Menu: EFFEROCYTOSE:target (v0.1 rule), SECRETE_CXCL9 (inflammatory; needs IFNγ), SECRETE_VEGFA_TGFB (suppressive; favoured by lactate/hypoxia in state, not forced), PATROL, WAIT. Polarisation is a reversible state with a minimum dwell time.

### 5.4 Endothelial
- State `perfused` (t=0: all perfused in baseline; hypoxia scenario declares a fraction non-perfused, chosen by seed).
- Menu when VEGF > threshold: SPROUT (tip cell; kernel extends a segment by displacing cells, H18), STAY_QUIESCENT. A new segment becomes perfused only after anastomosis + declared delay (MANUAL §14.2: geometry ≠ perfusion).
- Recruitment: perfused endothelium with CXCL9/10 above threshold admits new CD8 at a declared rate (**SIM influx**, off in baseline, on in `recruitment` scenario). This is how "the immune system sends more cells".

### 5.5 CAF / fibroblast
- Menu at tumour interface: DEPOSIT_MATRIX, SECRETE_TGFB, SECRETE_VEGFA (CAF only), WAIT. Matrix raises swap cost and drag → emergent immune exclusion (the missing mechanism named in the project notes).

### 5.6 CD4
- Menu: HELP_CD8:target (contact; grants `divisions_left` and exhaustion decay), MIGRATE_UP_CXCL9, WAIT. No Treg identity unless the Treg scenario is declared (FOXP3 4.1 %).

### 5.7 B and plasma cells
Quiet mechanical bodies by default (the primary follicle is a large obstacle between CD8 and tumour). B positioning / plasma secretion stay withheld as in v0.1 unless a later milestone adds them.

### 5.8 Virtual nerve (declared structure, absent from data)
- Placement options (declared per run): (a) a polyline through the stromal band between the follicle and the tumour front; (b) along the halo edge nearest the tumour; (c) none (control). Fixed geometry, occupies space, never decides.
- Emits NE-like and CGRP-like fields (toggle each).
- Declared effects (each a separate switch so their contributions can be ablated): NE → higher CD8 exhaustion accrual and lower motility (anchor: Globig et al. 2023, β1-adrenergic signalling and T-cell exhaustion); CGRP → higher CD8 exhaustion accrual (Balood et al. 2022, nociceptor CGRP–RAMP1); NE → tumour VEGF-A and cycle entry bias (adrenergic tumour-support literature; verify for lung). Implementer must verify every citation before use.
- Report nerve results only as "effect of a declared virtual nerve"; nothing in LUAD3 supports its presence or location.

## 6. Jev adapter v2

- Endpoint `POST https://api.typesafe.ai/v1/systemone`; pinned model (`jev-1.13.0` unless a newer version is verified via `GET /v1/models`); key only from `TYPESAFE_API_KEY` in the process environment (AGENTS.md).
- Batch ≤20 independent questions per request, ≤ ~12k tokens; lossless column/row tables; one `choice` question per queried cell. Shared `state` carries the model semantics once (definitions of states and actions, "kernel owns outcomes", "probabilities are preferences").
- Observation per cell (target ≤400 tokens): identity candidates + agreement; own SIM state; up to 6 contacts (id, primary label, interface, viability, relevant state such as PD-L1 or exhaustion); local field values as coarse bins with the `SIM` tag; distances to nearest tumour/endothelium; time since last stimulation; excluded options with reasons. No global counts, no target outcomes, no desired result.
- Validation **per question**: keys, legality, finite values; normalise sums within 2-decimal rounding (log raw values); if `choice` is not the argmax, apply the argmax only if the gap ≤0.02 and log it, else treat that one cell as `invalid_answer` (no new program). Other cells in the batch proceed. HTTP/transport failure → whole batch invalid, no retry, clocks continue (v0.1 failure policy).
- Budget: round-level pre-check (never start a round the cap cannot cover); `--max-requests` hard cap; journal every request/response to `audit.jsonl` before applying; resume reuses paid responses by request hash, never re-pays.
- **Dry-run estimator**: run the full model with LocalPolicy, count questions and batches per modeled hour, and print the calls needed for the chosen horizon before any paid run.
- Decision application: use the returned choice; probabilities are stored, never converted to rates. Optional scenario `sample_from_distribution` (seeded) must be labelled.

## 7. Scenarios (same seed, geometry and horizon unless stated)

| ID | Recognition | Recruitment | Hypoxia | Angiogenesis | Warburg menu | Nerve | Checkpoint |
|---|---|---|---|---|---|---|---|
| S0 baseline | unknown | off | off | off | off | none | — |
| S1 cognate | declared | off | off | off | on | none | — |
| S2 cognate + recruitment | declared | on | off | off | on | none | — |
| S3 hypoxic | declared | on | 50 % vessels non-perfused | off | on | none | — |
| S4 hypoxic + angiogenesis | declared | on | as S3 | on | on | none | — |
| S5 nerve NE | as S2 | | | | | NE | — |
| S6 nerve CGRP | as S2 | | | | | CGRP | — |
| S7 blockade | as S2 | | | | | none | PD-L1 term × declared factor |
| S8 blockade + nerve | as S7 | | | | | NE | as S7 |

Each scenario: LocalPolicy run(s) with several seeds (free) + Jev run(s). Report Jev vs LocalPolicy differences explicitly (MANUAL §17.6).

## 8. Readouts

Per tick and in the final report: live tumour cells and area (and in-ROI vs exited), divisions and blocked divisions; kills, CD8–tumour simulated contacts, CD8 within 20 µm of tumour, infiltration depth into the nest; exhaustion state fractions over time; recruited CD8; hypoxic and necrotic area; mean glycolytic fraction and lactate; vessel length and perfused length; nerve on/off deltas; decisions per type, invalid answers, calls and tokens. Every figure carries the scenario's declared assumptions.

## 9. Milestones with acceptance tests

| M | Deliverable | Accept when |
|---|---|---|
| M0 | Live smoke test: `scripts/jev_smoke_b26.py --live --max-requests 1` (≤10 calls total) | 20/20 answers valid or failure modes documented; latency, tokens, returned model recorded |
| M1 | Geometry + mechanics + swaps + division/removal, LocalPolicy only | IoU and contact-F1 at t=0 reported; no overlaps; accounting invariant; 72 h run < 5 min locally |
| M2 | Fields solver | mass balance; analytic test (single source, decay length); B26 baseline O2 map sanity (≈no hypoxia unless declared) |
| M3 | Programs §5 for CD8, tumour, macrophage, endothelial, CAF, CD4, virtual nerve | unit tests per program; v0.1 cognate outcome reproducible when motility/fields are off |
| M4 | Wake scheduler, menus via `conditions.py`, Jev adapter v2, dry-run estimator | synthetic-transport tests for batching, per-question failure, rounding, argmax gap, resume without re-pay, cap never exceeded |
| M5 | Pilot: S1 and S5 with ≤100 calls total | full audit; replay reproduces final state exactly; findings note written |
| M6 | Recording runs (cap set by the user after the pilot) | as M5, per scenario |
| M7 | Viewer: moving polygons, field overlays, exhaustion colouring, event timeline, run comparison; static export like Gut/LN | browser check, zero inference calls during replay |

Keep `pytest`, `scripts/validate_bundle.py --strict` and `scripts/verify_episodes.py` green after every milestone; update IMPLEMENTATION.md and CONTRACT_CORRECTIONS.md.

## 10. Hand-off prompt for the implementing model

> You are implementing `luad-runtime-0.2` in `D:/Life2026/VirtualTissue/LUAD/Xenium/luad-virtual-tissue`. Read `AGENTS.md`, `docs/PLAN_B26_AUTONOMOUS.md` (this file), `docs/PLAN.md`, `docs/IMPLEMENTATION.md`, `docs/CONTRACT_CORRECTIONS.md`, `contracts/runtime-v1.json`, `src/luad_tissue/*`, and MANUAL.md §§6, 11–17. For design lessons only (do not import code), read `jev.py`, `docs/LIVE_RUN.md` and `docs/CONTINUOUS_RESULTS.md` from https://github.com/hylixinsights/VirtualTissue-LN and the engine/manual contract of https://github.com/hylixinsights/VirtualTissue.
> Implement milestones M0–M4 and M7 in order, each with tests, without changing v0.1 behaviour. Keep all docs and code comments in English. All numbers are declared SIM assumptions in `contracts/runtime-v2.json`; verify every literature anchor before citing it. Jev chooses among kernel-validated options only; it never decides death, division outcome, identity or rates. The API key is available only as `TYPESAFE_API_KEY` in the process environment; never write it to disk, logs, episodes or the browser. Make no paid call beyond M0 (≤10 calls) and the M5 pilot (≤100 calls total) without the user's explicit new cap. Before any paid run, print the dry-run call estimate. Stop and report if the pilot shows systematic invalid answers, if one cell type consumes >50 % of questions, or if the tumour outcome depends only on a single declared parameter.
