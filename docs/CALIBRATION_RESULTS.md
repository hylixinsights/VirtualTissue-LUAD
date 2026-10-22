# Compression calibration: execution and results

**30 September update:** the explicitly authorized Jev campaign is completed and audited in [JEV_CAMPAIGN_5000.md](JEV_CAMPAIGN_5000.md). Earlier authorization/budget statements below preserve the historical 29 September record.

29 September 2026 · version 0.2.1. Five local-policy experiments completed 72 modeled hours, with the final solver and seed 21. Every saved numerical tick preserved all present cell bodies above its calibrated lower-area proxy within tolerance. These are mechanistic SIM results, not measured longitudinal outcomes or predictions for this patient. The live Jev trajectory is pending the specific data-egress authorization described below.

## Completed primary experiments

B26 starts with 139 tumor cells; B27 starts with 236. Live tumor counts include acting-lineage descendants beyond the original ROI. Death commitments are cumulative events, not simply initial minus final tumor: division can replenish the population.

| Region | Scenario | Live tumor at 72 h | Death commitments | Recruited CD8 | Peak zero-area bodies | Motionless 10 min ticks |
|---|---|---:|---:|---:|---:|---:|
| B26 | recognition_off | 250 | 0 | 0 | 0 | 0 / 432 |
| B26 | S1 | 79 | 121 | 0 | 0 | 5 / 432 |
| B26 | S2 | 53 | 133 | 239 | 0 | 3 / 432 |
| B26 | static | 139 | 0 | 0 | 0 | 432 / 432 |
| B27 | S1 | 437 | 47 | 0 | 0 | 2 / 432 |

S1 declares cognate recognition and functional effector competence. S2 adds declared recruitment and therefore tests insertion under crowding. The recognition-off control has the same competence assumptions but cannot kill; the exactly static control has no movement, decisions or events. B27 is a structural holdout, not an independent patient.

## Mechanical acceptance and remaining limitations

The original v0.2.0 recordings ended with 93 zero-area bodies in B26 S1, 228 in B26 S2 and 88 in B27 S1 (seed 21). The calibrated runs have zero throughout. This comparison includes the disabled dynamic weight rescue, new area constraints, delayed unobserved cycle initialization and safe insertion; it is not a controlled isolation of a single biological parameter.

An intermediate development candidate also eliminated zero-area cells, but globally froze motion in 168/432 B26 S1 ticks and 332/432 S2 ticks. It was rejected. The accepted solver uses contact-local damping and freezing; the corresponding final counts are 5/432 and 3/432. A tick is classified as motionless when its largest accepted substep displacement, recorded to four decimals, is below 0.00001 µm. Small whole-tissue fallback counts remain and are reported, not hidden.

| Region / scenario | Global rollbacks (substeps) | Blocked growth proposals | Rejected insertion trials | Median initial CD8 net displacement (µm) | Median initial B-cell net displacement (µm) |
|---|---:|---:|---:|---:|---:|
| B26 / recognition_off | 0 | 1402 | 227 | 106.25 | 2.97 |
| B26 / S1 | 148 | 3312 | 268 | 120.14 | 3.79 |
| B26 / S2 | 215 | 2780 | 163 | 109.29 | 3.42 |
| B26 / static | 0 | 0 | 0 | 0.00 | 0.00 |
| B27 / S1 | 39 | 1461 | 2381 | 79.96 | 7.13 |

There are 8,640 mechanical substeps per dynamic 72 h run. Net displacement compares the initial and final position of initial ROI cells still present; it is neither path length nor speed. Local freeze counters count body/pass operations and must not be interpreted as unique cells or biological arrest durations. Insertion trials include division and recruitment; rejected candidates create no cell and consume no biological birth count.

The smallest recorded area/proxy ratio across the five runs is 0.999999990766; the tiny excursion below one is within the declared 1e-8 relative geometry tolerance. Compression can still be substantial: the lower bound is a conservative type-level 2D proxy, not preservation of each nucleus's measured shape or area.

B27 initially contained five hidden power bodies under the legacy fit. An additional 134 damped fitting iterations, at unchanged measured sites, removed all five and placed every initial area within 1% of its measured target. Biological ratios were learned only from B26. This numerical reconstruction does not make B27 a kinetic validation set.

## Current-solver sensitivity checks

All entries below use B26 S1, seed 21, unchanged mobility 0.2, and six modeled hours. The primary factor 1.0 is selected from the empirical proxy before evaluating tumor outcomes. The 0.5-mobility development screens are exploratory and are not accepted evidence for a fitted migration coefficient.

| Proxy factor | Live tumor at 6 h | Peak zero-area bodies through 6 h | Minimum area/proxy ratio |
|---:|---:|---:|---:|
| 0.6 | 108 | 0 | 1.00000849 |
| 0.8 | 109 | 0 | 1.00000193 |
| 1.0 | 114 | 0 | 1.00000238 |

The short screens establish numerical feasibility and expose outcome sensitivity; they do not establish 72 h robustness across factors or seeds. The new 72 h profile has one seed per scenario. Original multi-seed runs remain available with their original contract and limitations.

## Verification and provenance

The full suite passed **96 tests in 55.73 seconds**. The strict reference validator reported 12 rules, 10 templates, 10 calibrated types, zero errors and zero warnings. All ten original B26/B27 contact-engine regression scenarios completed. Both the general autonomous verifier and the new compression verifier passed all five complete recordings.

Checks include engine and episode fingerprints; saved final positions; individual births, recruitment and fates; unchanged context accounting; quiet B/plasma cells; daily question caps; no killing without recognition; exact static positions; equal field domains and initial oxygen; field residuals and mass balance; and exhaustive final overlap. The source H5AD, supplied manual, rulebook and reference calibration retain their recorded hashes.

Authoritative private records are in `outputs/calibrated-final/` and the accepted viewer copies in `outputs/calibrated-release/`. Their `verification.json` and `calibration-verification.json` contain the full aggregate checks. Superseded development files stay under `outputs/calibration-20260929/` and are not accepted viewer defaults. The primary contract is `contracts/runtime-v2-calibrated.json`; see [method and literature](CALIBRATION.md).

## Viewer and delivery

The restarted loopback studio reports version 0.2.1 and exposes all five accepted recordings with a `calibrated-` catalog prefix. Browser inspection confirmed B26 S1 at 72 h (79 live tumor, 121 death commitments, zero zero-area bodies) and its same-time comparison with recognition-off (250 live tumor). The final six readouts fit one desktop row. No browser warnings or errors were recorded during this review.

The interface exported a captioned final frame, visually inspected and copied to `outputs/B26-calibrated-72h-preview.png`. The private `outputs/B26-calibrated-offline-player.html` embeds the matching atlas and episode with a verified checksum and no external style/script assets. Direct-file browser playback remains unverified because the browser tool blocked that protocol; the shared player code was verified in the loopback studio.

The allowlisted `dist/luad-virtual-tissue-0.2.1.zip` contains code, contracts, tests and English documentation. Raw inputs, per-cell recordings, environments, caches and credentials are excluded. `dist/calibration-delivery-verification.json` records archive integrity, source preservation, private-payload exclusion and test evidence. The archive is prepared locally; no GitHub repository has been created or published.

## Jev status and budget

Exactly **1 of the 1,500 authorized requests** has been sent. The smoke test returned `jev-1.13.0`, with 20/20 valid questions: 3 degranulation choices, 6 quiescence choices and 11 waits. This checks the protocol only; those choices were not applied to a live tissue trajectory. No further request was sent after the approval rejection.

The automatic approval review rejected the main live campaign because the API/cost authorization did not explicitly cover transmission of the Xenium-derived cellular payload to `https://api.typesafe.ai/v1/systemone`. A specific consent question was submitted to the user and remains unanswered at this delivery. The payload includes cellular identifiers and annotations, cell contacts and local simulated states. The ready runner uses hidden credential input, a persistent whole-campaign ledger, an inspected pilot and reuse of journaled responses without repayment. **1,499 requests remain; no live 72 h Jev trajectory is claimed.**

The matched local S1 control generated 19,313 decisions, grouped into an estimated 1,189 requests. This is not a forecast of the Jev trajectory: its choices, wake schedule and total calls may differ. The local S2 stress run would require an estimated 1,835 requests, so a 1,500-call campaign must not promise that trajectory will reach 72 h. Invalid responses, uncertain attempts and failures count against the global ceiling; there is no automatic retry.

The software and structural calibration are complete for this scope. Kinetic and clinical validation, a live Jev trajectory, repeated-seed calibration robustness, and new GitHub publication are not completed by these local results.
