# Autonomous run comparison

All numbers below describe declared local-policy SIM experiments, not observations or patient predictions.

| Region | Scenario | Seed | Hours | Live tumor | Death commitments | Recruited CD8 | Hypoxic tumor | Decisions | Estimated API requests |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| B26 | recognition_off | 21 | 72 | 267 | 0 | 0 | 0.0% | 17597 | 1125 |
| B26 | S0 | 21 | 72 | 282 | 0 | 0 | 0.0% | 1605 | 161 |
| B26 | S1 | 21 | 72 | 63 | 132 | 0 | 0.0% | 19496 | 1199 |
| B26 | S1 | 37 | 72 | 19 | 163 | 0 | 0.0% | 19180 | 1171 |
| B26 | S1 | 7 | 72 | 32 | 164 | 0 | 0.0% | 18959 | 1186 |
| B26 | S2 | 21 | 72 | 5 | 154 | 236 | 0.0% | 31957 | 1806 |
| B26 | S2 | 37 | 72 | 12 | 167 | 240 | 0.0% | 31540 | 1809 |
| B26 | S2 | 7 | 72 | 14 | 165 | 235 | 0.0% | 31551 | 1746 |
| B26 | S3 | 21 | 72 | 16 | 165 | 132 | 0.0% | 26314 | 1542 |
| B26 | S4 | 21 | 72 | 30 | 152 | 6 | 0.0% | 19446 | 1203 |
| B26 | S5 | 21 | 72 | 13 | 153 | 240 | 0.0% | 32226 | 1804 |
| B26 | S5 | 37 | 72 | 2 | 155 | 232 | 0.0% | 32008 | 1812 |
| B26 | S5 | 7 | 72 | 24 | 153 | 238 | 0.0% | 31980 | 1844 |
| B26 | S6 | 21 | 72 | 11 | 162 | 239 | 0.0% | 31591 | 1814 |
| B26 | S7 | 21 | 72 | 23 | 142 | 239 | 0.0% | 31912 | 1836 |
| B26 | S8 | 21 | 72 | 2 | 158 | 222 | 0.0% | 31795 | 1805 |
| B26 | static | 21 | 72 | 139 | 0 | 0 | 0.0% | 0 | 0 |
| B27 | S0 | 21 | 72 | 510 | 0 | 0 | 0.0% | 1366 | 249 |
| B27 | S1 | 21 | 72 | 441 | 45 | 0 | 0.0% | 15031 | 966 |
| B27 | S4 | 21 | 72 | 464 | 43 | 0 | 3.9% | 15557 | 993 |

Checks: episode and final-state fingerprints; exact saved final positions; individual accounting; no quiet B/plasma queries; per-cell daily caps; negative controls; field residual/mass balance; final non-overlap audit; identical field domains and matched initial oxygen for nerve controls.

An API estimate is derived from the local policy's actual menus and payload sizes. Jev may follow a different trajectory. No cost is inferred from this estimate.

Decision-concentration flags (>50% in one type) are reported in verification.json. Do not start a paid pilot without reviewing them. Hypoxia is an outcome: declaring half the vessels non-perfused does not guarantee a hypoxic patch.

## Reading the completed campaign

Twenty completed 72 h experiments were run with the declared local policy, with zero paid calls and zero invalid local answers. B26 has 17 recordings: all eleven scenarios at seed 21, plus seeds 7 and 37 for S1, S2 and S5. B27 has three secondary recordings, S0/S1/S4 at seed 21. These are model realizations, not biological replicates. Death commitments are cumulative and tumor cells can be born during a run; they must not be subtracted from the initial tumor count without the birth/death accounting.

B26 starts with 139 tumor cells. The exactly static control retains all 139 with unchanged positions, no questions and no events. Recognition-off ends with 267 live tumor cells and zero cytotoxic pulses or death commitments; S1 at the same seed ends with 63 and 132 commitments. S0 ends with 282, but also changes the identity policy and therefore is not a pure recognition ablation. In S1, the final tumor count ranges from 19 to 63 across three seeds; one seed is not a stable effect estimate.

Declared CD8 recruitment (S2) produces 5–14 remaining tumor cells and 235–240 recruited CD8 cells across those seeds. Recruitment has a strong effect under this local controller and these proposed rates; it is not measured influx. The seed-matched NE comparison is S5 minus S2: +10 live tumor cells at seed 7, +8 at seed 21 and −10 at seed 37. The direction changes with seed. Do not claim a reproducible tumor-promoting or protective nerve effect from this campaign. S6 versus S2 tests CGRP at one seed; S8 versus S7 tests NE with the declared blockade switch. S1 versus S5 also changes recruitment.

No B26 scenario is hypoxic at 72 h under the proposed nutrient sources, including the half-perfusion conditions. B27 S4 has a 3.9% final hypoxic tumor fraction. This outcome was retained rather than tuning the sources to force hypoxia. B27 S1 ends with 441 live tumor cells and 45 death commitments; its different initial composition and geometry prevent a direct treatment-effect interpretation of B26 versus B27.

## Mechanical and inference limitations

Crowding is material. In B26 S1 seed 21, 93 modeled bodies have zero power-cell area at 72 h, while remaining present in individual accounting. Mean pressure is 0.188 in the model's dimensionless units. These bodies have not died merely because they have no visible polygon. The interface displays this count; cell IDs, states and mechanical diagnostics remain in the recording. Shape fitting at time zero does not validate later mechanics. Boundary confinement, compression and cell insertion must be calibrated before interpreting magnitudes as tissue predictions.

All nonstatic B26 runs flag CD8 as more than half of questions. The scheduler honors the per-cell cap, but a paid pilot must still review that concentration. Local-priority decisions and their one-hot probabilities are explicitly programmed assumptions. They do not establish Jev behavior, measured cell policies, antigen specificity or clinically useful predictions.

## Release diagnostics

| Region | Scenario | Seed | Zero-area bodies at 72 h | Mean SIM pressure | Perfused new segment length (µm) |
|---|---|---:|---:|---:|---:|
| B26 | recognition_off | 21 | 1 | 0.142 | 0.00 |
| B26 | S0 | 21 | 0 | 0.123 | 0.00 |
| B26 | S1 | 21 | 93 | 0.188 | 0.00 |
| B26 | S1 | 37 | 103 | 0.179 | 0.00 |
| B26 | S1 | 7 | 99 | 0.192 | 0.00 |
| B26 | S2 | 21 | 228 | 0.306 | 0.00 |
| B26 | S2 | 37 | 229 | 0.288 | 0.00 |
| B26 | S2 | 7 | 258 | 0.315 | 0.00 |
| B26 | S3 | 21 | 333 | 0.304 | 0.00 |
| B26 | S4 | 21 | 96 | 0.188 | 6.92 |
| B26 | S5 | 21 | 251 | 0.288 | 0.00 |
| B26 | S5 | 37 | 84 | 0.243 | 0.00 |
| B26 | S5 | 7 | 305 | 0.325 | 0.00 |
| B26 | S6 | 21 | 306 | 0.323 | 0.00 |
| B26 | S7 | 21 | 317 | 0.320 | 0.00 |
| B26 | S8 | 21 | 159 | 0.258 | 0.00 |
| B26 | static | 21 | 0 | 0.000 | 0.00 |
| B27 | S0 | 21 | 1 | 0.177 | 0.00 |
| B27 | S1 | 21 | 88 | 0.229 | 0.00 |
| B27 | S4 | 21 | 117 | 0.241 | 0.00 |

Raw atlas and per-cell episodes remain private under `outputs/`. This document contains aggregate results only. All five nerve recordings use the corrected common field domain; superseded development recordings are excluded.
