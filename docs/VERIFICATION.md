# Verification record

**30 September update:** the explicitly authorized Jev campaign is completed and audited in [JEV_CAMPAIGN_5000.md](JEV_CAMPAIGN_5000.md). Earlier authorization/budget statements below preserve the historical 29 September record.

The evidence below records the original v0.2.0 delivery. The subsequent v0.2.1 compression calibration, 96-test suite and live Jev smoke test are documented in [CALIBRATION.md](CALIBRATION.md) and [CALIBRATION_RESULTS.md](CALIBRATION_RESULTS.md).

Run date: 29 September 2026. Local Windows runtime: Python 3.12.14 with the exact packages in `requirements.lock`. The Linux-created `.venv` found at resumption was preserved under `.cache/venv-wsl-20260925`; the working Windows environment was rebuilt from the lock.

## Reference preservation and regression

The existing 60-test suite passed before extending the runtime. The final expanded suite passed **89 tests in 48.77 seconds**, covering the fields, programs, provider, episode integrity and local server. The strict reference validator reported 12 rules, 10 question templates, 10 calibrated cell types, zero errors and zero warnings. Both browser JavaScript entry points passed syntax checks.

The v0.1 real-data checker completed all ten B26/B27 scenarios. Baseline and recognition-off had zero decisions and zero events. B26 cognate/blockade ended with 990 alive and 10 intact dead cells; checkpoint left all 1,000 alive. B27 cognate/blockade ended with 998 alive, one intact dead and one cleared cell; checkpoint left all 1,000 alive. These are regression controls for the original contact engine, not the autonomous 72 h results.

## Autonomous numerical and biological checks

Tests exercise a constant reaction–diffusion solution, conservative source deposition, analytic decay length of a single line source, mass balance and spatial gradients. Program tests cover unknown recognition, legal degranulation, contact-loss cancellation without spending material, clocked individual metabolic changes, death and necrosis accounting, finite one-time clearance, CD4 help and CD8 division material partition, all secretory source types, persistent matrix, delayed sprout perfusion, gated recruitment and declared nerve sources. The static control preserves exact site positions without questions or events.

Provider tests cover question/byte batching, rounded probabilities, small argmax repairs, per-cell invalid responses, complete-round budget checks, durable resume without repayment, uncertain intent handling, redaction and returned-model changes. They use synthetic transport and make no paid calls.

The autonomous runner writes an episode and report for each scenario/seed. Completed-run verification checks both fingerprints, exact final saved positions and viability, individual and context accounting, daily decision caps, quiet B/plasma behavior, negative controls, field balance and exhaustive final overlap. The authoritative generated comparison is `outputs/autonomous-release/RESULTS.md` with machine-readable `verification.json`.

## Completed 72 h campaign

Twenty completed recordings reached 72 modeled hours: 17 B26 and three B27. All passed fingerprint, final-frame, accounting, negative-control, quiet-cell, daily-cap, saved-frame field-balance/residual and exhaustive final-overlap checks. All scenarios for the same atlas use equal field-grid geometry; matched nerve controls have identical initial oxygen. Five nerve trajectories were repeated after correcting a development-only field-domain confound; the superseded recordings are excluded. See [aggregate results and limitations](RESULTS.md).

The B26 static control retained exact positions and 139 live tumor cells with zero events or decisions. Recognition-off ended with 267 live tumor cells and no killing. S1 ended with 19–63 live tumor cells across seeds 7, 21 and 37. These outcomes verify execution of the declared rules, not biological validity. In S1 seed 21, 93 bodies have zero power-cell area at 72 h; they remain tracked. Mechanical crowding and seed variation are explicit limits on interpretation.

Every completed recording used `LocalPolicyV2`: zero paid requests and zero invalid local answers. The M0 smoke utility generated 20 kernel-validated questions in a 31,565-byte batch without sending it. Synthetic transport tests validate protocol handling; no live Jev response was obtained.

## Browser and portable replay

The loopback viewer was reviewed with real recordings: initial measured polygons, 72 h playback and seeking, viability and oxygen overlays, cell 95048's dual identity and recorded decisions, S1/S0 comparison, compressed-record import and verified fingerprints. A new B27 S1 experiment advanced one modeled hour and saved 670 local decisions. A 390 × 844 responsive check had no horizontal overflow. Temporary viewport overrides were reset. No browser error or warning was recorded in those checks.

The captioned 72 h B26 S1 PNG was exported through the interface to `outputs/views/` and visually inspected; the convenience copy is `outputs/B26-72h-preview.png`. Private outputs contain per-cell geometry and are excluded from the release.

The standalone HTML embeds its atlas and recording with a payload checksum and no external script/style assets. Export and corruption checks passed. Automated opening of `file://` was blocked by the browser tool's protocol policy, so direct-file playback was not visually verified in that tool. The same player code was exercised through the loopback viewer.

## Delivery boundary

English documentation covers setup, model assumptions, operational corrections, controls, results, provenance and future GitHub export. The allowlisted release is produced by `scripts/package_release.py`; its separate manifest records a SHA-256 hash for every included file. The raw-data and reference preservation checks and final archive audit are recorded in `dist/delivery-verification.json`.

No live Jev request, paid pilot, patient calibration or GitHub publication was performed as part of this implementation. Live M0/M5/M6 remain separate experiments. All biological mechanisms and numerical rates in v0.2 are declared model assumptions.
