# Recorded Jev campaign: 5,000-request ceiling

30 September 2026. B26 S1, seed 21, the previously validated structural compression contract and an unchanged numerical kernel. The user explicitly authorized the Xenium-derived cellular payload to the official Jev endpoint and raised the cumulative ceiling to 5,000 requests. The earlier one-request smoke test remains counted.

## Recorded outcome

The actual Jev trajectory reached **72 modeled hours**, stopping with `horizon_reached`. It used **1,059 new HTTP requests**, carrying **17,071 individual cellular decisions**. Including the earlier smoke, cumulative use is **1,060 / 5,000 requests**; **3,940** remain unused. A ceiling is not a requirement to spend the remaining calls after the planned 72 h experiment ends.

Returned model: `jev-1.13.0`. Invalid individual answers: **0**. Unknown-usage requests in this trajectory: **0**. No automatic retry, policy substitution, mid-run prompt revision or outcome-based stopping was used.

| Quantity | Jev recording | Matched local-policy control |
|---|---:|---:|
| Live tumor at final time | 94 | 79 |
| Cumulative death commitments | 45 | 121 |
| Physical divisions (all lineages) | 0 | 116 |
| Recruited CD8 | 0 | 0 |
| Peak zero-area bodies | 0 | 0 |
| Terminally exhausted CD8 at final time | 10 | 11 |

Both trajectories start from 139 tumor cells in the same 1,000-cell ROI with 441 context objects. Death commitments and divisions are cumulative; a final population difference is not itself a measured killing rate. Recognition and functional competence are declared S1 assumptions. These outcomes do not establish patient-level predictive validity.

## Decisions and pilot review

The first round contained 240 questions in 12 requests. All 240 returned valid responses. The concentration flag reflected 126 initially proliferating tumor cells (52.5% of the questions), not CD8 overuse. All 139 initial tumor choices were quiescence, while 10 contact-licensed CD8 choices were degranulation. The initial pilot was inspected and then reused from its journal without repayment. Quiet B/plasma and context cells remained unqueried.

| Chosen behavior | Count |
|---|---:|
| DEGRANULATE | 186 |
| EFFEROCYTOSE | 2 |
| HOLD_CONTACT | 601 |
| HOLD_POSITION | 12,004 |
| MIGRATE_UP_CXCL9 | 2,212 |
| REMAIN_QUIESCENT | 658 |
| REST | 10 |
| SECRETE_CXCL9 | 2 |
| WAIT | 1,396 |

| Cell type | Individual decisions |
|---|---:|
| CAF | 81 |
| Fibroblast | 122 |
| Macrophage_SPP1 | 679 |
| T_CD4 | 795 |
| T_CD8_cytotoxic | 14,736 |
| Tumor | 64 |
| Tumor_proliferating | 594 |

Across the full trajectory, CD8 cells received 86.3% of questions. This reflects the declared wake scheduler and eligibility, not independent evidence of cellular importance. Repeated hold choices are visible in the receipts. Jev selected no proliferative behavior; the lack of division is therefore a policy outcome in this experiment, not proof of absent tumor proliferation in the biopsy. No growth or insertion trial was blocked in this trajectory.

All decisions match a saved Jev reply, exact local observation and permitted menu. Rounding/argmax repairs under the predeclared tolerances: `{"rounded_sum_normalized": 130, "small_argmax_gap": 4}`. Raw replies remain preserved in the local journal; repaired preferences never become biological rates.

## Mechanical and numerical verification

Peak zero-area bodies: **0**. Minimum area/proxy ratio: **1.0000000538**. Motionless ticks: **4 / 432**. Global substep rollbacks: **143**. Rejected growth proposals: **0**. Rejected insertion trials: **0**.

The generalized recording verifier and compression verifier passed. They check geometry, final overlap, identity/fate accounting, field balance and residuals, quiet-cell exclusion, per-cell daily question caps and saved-state integrity. The earlier calibration controls and source data are preserved.

A second execution reconstructed every biological decision, event, numerical metric, body, saved frame and final state from the durable journal. It matched exactly, used **zero new HTTP requests**, and left the journal unchanged. Final-state fingerprint: `0a84d5eb52345e38732f63cb73a323880458cd7319a894e4714ebca2b05200ba`.

The complete suite passed **103 tests in 55.05 seconds**. The strict reference validator reported zero errors/warnings. Test providers are synthetic; actual Jev validation is evidenced separately by this paid recording and receipt audit.

## Reported usage

The main trajectory reports `{"input_tokens": 13406643, "output_tokens": 979629}` tokens. The earlier smoke reports `{"input_tokens": 15421, "output_tokens": 1346}`. These are distinct sets of requests; do not count the cached pilot again. No dollar cost or current service tariff is inferred here.

## Replay and GitHub preparation

`outputs/publication/jev-site/` is the selected static replay. Event chapters, cell inspection, next-frame/final-state controls and the provenance page read saved data. Event time and saved-frame time are labeled separately. Its Content Security Policy disables network connections, and playback requires no key or inference service.

Prepared artifacts:

- `dist/VirtualTissue-LUAD-ready-to-upload.zip`: allowlisted source plus the selected replay for the specified repository.
- `dist/VirtualTissue-LUAD-static-replay.zip`: only the static player and selected recording.
- `outputs/github-upload/VirtualTissue-LUAD/`: expanded repository with upload instructions and file hashes.
- `outputs/jev-campaign-20260930-5000/`: private journals, original checkpoints, verification and reconstruction evidence.

The selected upload package contains per-cell Xenium-derived observations and geometry. It is not anonymized. Raw H5AD inputs, unselected runs, API journals, credentials and local environments remain excluded. No repository push or website deployment was performed. See [GitHub instructions](GITHUB_RELEASE.md) and [the LN review](LN_REVIEW.md).
