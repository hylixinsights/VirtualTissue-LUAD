# Implemented model, version 0.1.0

**Current release: 0.2.1.** The autonomous mechanics/fields/programs/scheduler/provider/viewer extension is documented in [AUTONOMOUS_RUNTIME.md](AUTONOMOUS_RUNTIME.md), with measured structural compression constraints in [CALIBRATION.md](CALIBRATION.md). The completed 72 h Jev recording and request accounting are in [JEV_CAMPAIGN_5000.md](JEV_CAMPAIGN_5000.md). The viewer now has recorded event chapters and a selected static replay, prepared locally for later GitHub publication. The v0.1 description and M1 results below are preserved as version-specific records, not the scope of the current release. See [VERIFICATION.md](VERIFICATION.md) for current checks.

The runtime is a fixed-geometry contact laboratory on two measured LUAD3 patches. Its scope is deliberately explicit: it reconstructs the section and implements timed cytotoxic damage, conditional death and macrophage clearance. It does not yet implement the broader planned tissue dynamics.

## State ownership

`atlas.py` reads the H5AD and segmentation CSV, verifies the H5AD against the frozen specification, imports both annotations and 20 scores, reconstructs contacts and adds a 30 µm polygon halo. Exact polygon coordinates are preserved, with any validity repairs listed in provenance. Contact is polygon distance ≤1 µm. Interface length remains the original approximate buffered-overlap estimator.

ROI observations are immutable. The separate runtime state contains viability, dimensionless cumulative damage, finite cytotoxic pulses, a cooldown, decision due time, finite macrophage capacity and one active program. Context cells remain frozen. Occluded objects occupy space and never receive a repertoire. Neither source transcript values nor annotation labels evolve during a run.

`conditions.py` distinguishes reference conditions from executable conditions. A complete action requires identity, all reference prerequisites, current actor availability, any additional mechanism prerequisites and an implemented handler. The report contains true, false and unknown for each condition. The UI selects a representative interface with the fewest blockers; the API includes every evaluated interface.

## Explicit model assumptions

All numbers below are SIM assumptions, not experimentally fitted rates. The authoritative values are embedded in every episode's runtime contract.

| Parameter | Value |
|---|---:|
| Integration/clock tick | 10 modeled minutes |
| Minimum decision interval | 30 modeled minutes |
| Cytotoxic contact program | 20 modeled minutes |
| Cooldown following a delivered pulse | 60 modeled minutes |
| Initial finite pulses per declared CD8 | 3 |
| Damage per pulse without assigned inhibition | 1 arbitrary unit |
| Commitment threshold | 2 arbitrary units |
| Time from commitment to intact death | 30 modeled minutes |
| Macrophage clearance program | 40 modeled minutes |
| Lifetime target-processing allowance | 2 targets per macrophage |
| Assigned checkpoint damage multiplier | 0.25 |
| Assigned blockade damage multiplier | 1.0 |
| Experiment horizon | 360 modeled minutes |

Baseline uses conservative capability intersection and unknown recognition/effector competence. The recognition-off control declares primary-annotation competence but explicitly denies recognition. Cognate, checkpoint and blockade scenarios use the same geometry and primary-annotation policy and declare recognition for qualifying CD8–tumor interfaces. No tumor-specific antigen was measured. Checkpoint and blockade are toy sensitivity cases: the assigned multiplier is not a predicted drug effect, and a successful reversal is largely a consequence of that assumption.

## Event ordering

Each round first derives menus from a common snapshot. All provider answers are validated before any new program starts. Seeded arbitration prevents competing cells from reserving the same participant in that round. Timed programs execute without a second query. No actor can start another program while busy or before its decision interval; the cooldown additionally constrains degranulation.

A completed cytotoxic program rechecks contact, target viability and available effector material. One pulse is spent only on delivery. Damage reaching threshold commits the target to apoptosis and cancels its active program. Death completes on its clock. A macrophage can clear an apoptotic/dead contacting target, once, if capacity remains. Clearance is separately logged and consumes one capacity unit. There is no regeneration, damage repair, corpse movement, tissue relaxation or renewal of processing capacity.

The original atlas is not edited by these outcomes. Displaying a cleared polygon as empty is an outcome of the removal mechanism; other cells do not move into that space in this version. Total individual accounting remains alive + apoptotic + dead intact + cleared = initial ROI count.

## Decisions and failure

The local preview takes the first permitted active option in descending measured interface order, otherwise waits. Seeded arbitration handles competition. This is a declared mechanistic control policy with one-hot bookkeeping probabilities, not Jev and not inferred biology.

The optional Jev adapter uses one request per cell, a pinned model and a positive request budget. It submits local state and permitted options only; it checks question keys, choice membership, normalized finite probabilities, confidence and returned model continuity. There are no retries. Invalid/partial rounds start no new programs; preceding mandatory clocks continue and failures are visible. Request-cap refusal stops before an unaffordable complete round. Paid usage can be unknown after a failed request.

Live calls are available only through the explicit recorder command. The browser always uses the local policy and holds no API key. The adapter's protocol was checked against [TypeSafe Choice documentation](https://docs.typesafe.ai/primitives/choice) on 23 September 2026 and tested with synthetic transport. No live connection or outcome was tested.

## Recording and interface

Every clock step is saved atomically in a private local episode. Every queried cell retains its exact observation, menu, probabilities, answer and receipt. All events and per-tick states are saved. An episode embeds the full runtime contract and the atlas fingerprint. A new browser experiment gets a new output name; previously saved runs remain on disk.

The browser imports a compressed episode, verifies its fingerprint through the local server, checks the matching atlas, and displays its saved frames and decisions. Seeking does not simulate biology or call inference. The server only exposes the explicitly listed web files and API routes on loopback. Replay requires the corresponding atlas build, not raw Xenium inputs or an API key. Resume of a saved simulation is not implemented; replay is distinct from continuation.

## Unimplemented mechanisms

Movement and deformable mechanics, proliferation/division, dynamic matrix, chemokine/cytokine transport, antigen processing/display, co-stimulation, plasmocyte secretion, hypoxia, angiogenesis/perfusion, inflammation, resistance, GC, SHM, class switching and recruitment/egress have no physical handlers in this version. Their reference rules remain visible and blocked. The next planned milestone is deformable mechanics followed by an explicit CD8 migration rule.

# luad-runtime-0.2.0.dev1 — milestone M1 (moving geometry)

Implemented 25 September 2026 under `src/luad_tissue/v2/` with contract `contracts/runtime-v2.json`. It follows `docs/PLAN_B26_AUTONOMOUS.md` §3.1 with the deviations listed in `docs/CONTRACT_CORRECTIONS.md` (v0.2 section). The v0.1 runtime, contract, tests and saved episodes are unchanged; `scripts/verify_episodes.py` reproduces the existing `outputs/episode-verification.json` byte for byte. M1 contains no biological handler: no killing, fields, recruitment or Jev. Its only policy is a declared mechanics exercise.

## Modules

| Module | Role |
|---|---|
| `geometry.py` | Bounded power (Laguerre) diagram: power cell ∩ own disk (weight = radius²). Lower convex hull of lifted sites (Qhull); areas, interface lengths and gaps in closed form, vectorised. Cells tile the union of disks and cannot overlap. ~7 ms for 1,500 bodies. |
| `mechanics.py` | Mutable `Tissue`: weight fit, one-sided pressure, overdamped relaxation, viscoelastic anchoring, hard-core projection, wall, division, removal, contact handover, accounting and invariants. |
| `local_policy.py` | `M1ExercisePolicy`: ranks kernel-built menus, one-hot bookkeeping probabilities. |
| `runtime.py` | `SimulationV2`: tick loop (decisions → substeps → clocks → tracking/readouts), self-propelled or swap motility, tumour cycle clock, episode `luad-episode-v2-m1`. |
| `fidelity.py` | t=0 IoU per type and contact-graph F1 against the measured polygons. |
| `scripts/run_v2_mechanics.py` | Runs scenarios on a built atlas and writes private episodes plus one merged report under `outputs/v2/`. |

## Mechanics as implemented

- **Initial condition.** Each measured polygon becomes a site at its polygon centroid. A per-cell factor κ (radius² = κ·A0) is fitted (80 iterations) so each simulated area matches the measured area; the fitted t=0 area then becomes the target area A0. The measured configuration is therefore a declared mechanical equilibrium: zero pressure and zero force at t=0.
- **Pressure and force.** One-sided pressure P = max(0, (A0 − A)/A0): cells resist compression, with no cohesive tension. Force F_i = −Σ_j ((P_i + P_j)/2)·L_ij·n_ij over shared interfaces. The arc of the disk is the free surface, so compressed cells at a free edge push outward, and uniform pressure inside a closed ring gives no net force.
- **Viscoelastic anchoring.** v −= k·(x − anchor). The anchor creeps toward the site (τ = 6 h), so a brief push recovers and sustained growth pressure causes lasting displacement. k = 0.2/min for tumour, stroma, endothelium and occluded objects; 0.05/min for immune cells. Self-propelled cells carry their anchor with them.
- **Hard core.** Power-adjacent sites are projected apart to max(0.35·(ρ_i+ρ_j), √|w_i − w_j| + 1 µm), the two-body condition for neither cell to vanish. Pairs that were already closer at t=0 keep their t=0 distance.
- **Domain.** ROI and halo are mechanically active. Context bodies beyond roi_radius + halo − 12 µm are fixed. A wall at that radius confines mobile sites, and every confinement is counted.
- **Motility (default `self_propelled`).** v0·heading·traction. The heading persists for 10 min. Traction is the interface-weighted permeability of current neighbours divided by max(Σ interface, 0.75 × equal-area circumference), so a cell cannot crawl across empty space. Neighbour exchanges occur as topological changes of the diagram. The plan's discrete `swap` mode remains selectable for comparison.
- **Cycle and division (kernel clocks).** Accelerated 24 h tumour cycle, explicitly labelled. The target area rises linearly to 2·A0. At the due time the cell divides along the long axis of its simulated cell (one daughter is born and the parent keeps its identity) unless local pressure > 0.25, which records `division_blocked_crowding`. Cycle entry is offered only when local pressure ≤ 0.15. A single legal option is never queried.
- **Removal.** `remove()` records a fate. Neighbours take the space through their disks and by pressure. Removed identities are never reused.
- **Contacts.** H04 applies to simulated cells: power-adjacent bodies with a shared interface or a disk gap ≤ 1 µm. **Handover:** at t=0 the runtime graph is exactly the measured polygon graph. A t=0 pair keeps its measured status while its site distance stays within 1 µm of the t=0 value; after that the simulated geometry decides. Provenance is `measured_contact_persisting` or `simulated_contact`.
- **Invariants checked every tick.** Acting accounting (alive in ROI + alive outside ROI + removed fates = initial ROI + born + recruited); context accounting; unique identities; finite state; fixed bodies never move; no acting body is fixed. The runner also audits overlap exhaustively (summed polygon area versus union) at t=0 and at the end.

## M1 results on B26 (seed 21, 72 modeled hours, local VM, Python 3.12, `requirements.lock`)

**t=0 fidelity.** The area fit reaches 0.9997–1.0003 (5th–95th percentile) with no hidden cell and no κ at its bounds. Median IoU against the measured polygons, ROI cells: 0.776 (IQR 0.72–0.82). By type the median ranges from 0.67 for Tumor (n=13) to 0.79 for B cells. Equal-area radii without the fit give 0.740.

**Contacts.** Pairs with at least one ROI cell, simulated geometry alone: precision 0.986, recall 0.835, F1 0.905 (3,530 measured pairs). CD8–tumour: 12 of 19 recovered (F1 0.75). Without the fit, F1 is 0.79. The handover rule makes the runtime graph at t=0 identical to the measured graph (19/19 CD8–tumour).

| Run | Wall time | Result |
|---|---:|---|
| `static` (null control) | 68 s | Exactly static for 72 h: zero displacement, zero pressure, the 19 measured CD8–tumour contacts persist. |
| `m1_exercise`, self-propelled | 79 s | Tumour cells 139 → 297; 158 divisions, 117 blocked-division events; mean pressure 0.16; 14 hidden bodies at the end; exhaustive overlap 0. Median net displacement of passive bodies: endothelium 2.1 µm, occluded 2.1, B 4.1, tumour 4.9–7.0, CAF 6.3 µm. CD8 realised path speed 1.46 µm/min (declared 4). Seed 7 gives the same picture: 296 tumour cells, pressure 0.16, 9 hidden. |
| `m1_exercise`, swap (plan alternative) | 82 s | Passive bodies scrambled: median displacement 36–58 µm (endothelium 49 µm), 429 hidden bodies, mean pressure 0.45, and tumour cells 424 because exchanges carry tumour cells into less crowded places. Rejected as the default. |

The 72 h target (< 5 min) is met. Exercise-run readouts are properties of a declared mechanics exercise, not biology.

## Known M1 limitations to carry into M2/M3

- Growth happens in a confined domain. Pressure builds against the wall and fixed ring, so any growth or containment result must be tested for sensitivity to the fixed-ring width, the wall and the mobility.
- Compressed tissue expands into measured voids: covered area rose 109.3k → 125.9k µm² (+15 %) in the exercise run. Whether B26 voids are airspace or segmentation gaps is unknown. Reported, not tuned away.
- Self-propelled CD8 cells squeeze themselves and their neighbours: mean CD8 pressure at 72 h is 0.23 (seeds 21 and 7) and rescues accumulate. The local-pressure gate for tumour division therefore feels CD8 traffic, and M3 should decide whether that coupling is intended.
- The declared CD8 speed (4 µm/min) and the persistence time are unverified anchors. In the exercise every CD8 scans continuously, so net displacement (median 144 µm in 72 h) is not a prediction. M3 menus (HOLD/REST, chemotaxis) will change this.
- Raw simulated contact recall is 0.84. The handover rule hides that at t=0, but contacts that the power diagram cannot represent (elongated or concave polygons) are lost as soon as their cells move.
