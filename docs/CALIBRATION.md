# Structural biological calibration and bounded Jev campaign

**30 September update:** the explicitly authorized Jev campaign is completed and audited in [JEV_CAMPAIGN_5000.md](JEV_CAMPAIGN_5000.md). Earlier authorization/budget statements below preserve the historical 29 September record.

29 September 2026. The user authorized biological calibration and at most 1,500 Jev requests across the whole campaign. Requests include smoke tests, pilots and failures. The secret is entered through a hidden terminal prompt or process environment; it is not written to a file or sent to the browser.

## What these measurements can identify

The supplied H5AD contains both `nucleus_area` and `cell_area`, joined through `cell_id`. All 1,000 B26 ROI cells have valid positive measurements with nucleus area no greater than cell area. Their dimensionless ratios support a lower-area proxy for each primary cell type. They do not identify elastic modulus, 3D volume, time-dependent shrinkage, motility speed, cycle duration, cytotoxic potency or drug response.

The primary structural profile uses the B26 10th percentile of nucleus/cell area by type, bounded to 0.1–0.8, multiplied by each body's fitted initial target area. Types with fewer than five training cells and unannotated context use the pooled B26 fallback. This conservative population proxy is not a measured nuclear boundary for each individual cell. Its factor is 1.0; factors 0.6 and 0.8 are sensitivity checks. The original mobility coefficient 0.2 is retained because it cannot be identified from a static section; 0.5 is an exploratory numerical comparison. Tumor survival does not select the profile. B27 does not contribute to its biological ratios.

`contracts/runtime-v2-calibrated.json` records the measurements, sample counts, quantiles, source hash and operational choices. The supplied `rulebook/calibration.json`, biological manual and original runtime contract are preserved.

## Corrections to mechanics and cell growth

The previous dynamic rescue increased the power weight of compressed cells. This could compress adjacent cells and create further hidden objects. That rescue is disabled in the calibrated profile. Motion proposals are tested against the area proxy, and only violating contact neighborhoods are backtracked. Power-adjacent cells separated by an empty gap do not transmit a local rollback. Persistent violations freeze the affected neighborhood while leaving independent motion intact. The accepted displacement, not the rejected proposal, contributes to path length. Fixed context positions remain exact.

An intermediate development solver fell back too often to a whole-tissue rollback: B26 S1 had 168 motionless ticks out of 432, and the S2 stress test had 332. Those candidates were rejected even though they had zero hidden cells. The final solver adds local rollback and a regression test with two separate tissue islands. Both visibility and remaining motion are audited; zero hidden cells alone is not an acceptance criterion.

Growth proposals are evaluated together. A blocked neighborhood postpones its growth clock. Daughter placement and recruitment must pass the same check for every existing body and the proposed new body. Recruitment searches eight local positions outside the vessel center and defers an insertion when none fits. No birth or influx is counted until insertion succeeds. Death and clearance remain explicit biological events; compression alone does not manufacture death.

An unobserved random cycle phase previously created immediate target-area jumps in cells annotated as proliferating. The calibrated profile begins growth at licensed entry without those jumps. The accelerated cycle duration itself remains an assumption. This correction is included in the profile, so its comparison with v0.2.0 is a composite mechanics/initialization correction, not an isolated estimate of compression biology.

B27 exposed five already-hidden cells after the original initialization fit. A damped fallback at unchanged measured sites removed them in 134 additional iterations, with every reconstructed area within 1% of its measured target. This is numerical reconstruction of the holdout's observed geometry, not fitting its biological parameters. Measured t=0 polygons and the measured contact handover remain available.

## Literature support and limits

[Salmon et al., JCI (2012)](https://www.jci.org/articles/view/45817) examined T-cell localization and migration in human lung tumor slices and implicated matrix architecture in access to tumor islets. This supports retaining spatial barriers and inspecting displacement instead of treating contact as a freely mixed process. It does not calibrate the numerical mobility or permeability of this particular section.

[Delarue et al., Biophysical Journal (2014)](https://doi.org/10.1016/j.bpj.2014.08.031) linked compression-induced volume reduction to reversible proliferation inhibition in tumor spheroids. This motivates withholding growth under crowding. The cell lines, 3D setup and measured stresses are not this LUAD biopsy, so no pressure in kPa or kinetic coefficient is imported from that experiment.

## Verification and paid inference

The checks cover aggressive motion, rejected growth and insertion without state mutation, exact static geometry, preservation of every initial B27 body, individual accounting and a persistent request cap. Long runs inspect the minimum area/proxy ratio, zero-area bodies, overlap, field balances, displacement and deferred growth/insertion. The primary profile and sensitivity experiments are selected independently of an intended tumor outcome.

The first live smoke batch used `jev-1.13.0` and validated all 20 questions with one request. [The official Choice/API contract](https://docs.typesafe.ai/api) defines the structured payload and response; response validity does not validate the biological choices. The adapter enforces kernel menus, model continuity, finite distributions and independent clocks. It never converts probabilities into biological rates.

`scripts/run_jev_campaign.py` performs a local dry run, records a paid pilot, pauses for inspection of a concentration flag, and can reconstruct the continuation using cached replies without repayment. It uses a whole-campaign ledger under `outputs/jev-campaign-20260929/` in addition to each run's journal. Unknown or failed attempts consume the ceiling. The secret never appears in those journals. Protocol failures stop for inspection, without automatic retries or a local-policy substitution.

Execution counts and completed-run results are reported separately in `CALIBRATION_RESULTS.md`. A software pass or valid Jev response is not patient-level predictive validation.
