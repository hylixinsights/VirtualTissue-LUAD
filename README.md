# LUAD Tissue Studio

Repository destination: [hylixinsights/VirtualTissue-LUAD](https://github.com/hylixinsights/VirtualTissue-LUAD). The 30 September Jev campaign completed 72 modeled hours: 1,059 new requests, 1,060 cumulatively against the authorized 5,000 ceiling, and 17,071 individual decisions. See [the recorded campaign](docs/JEV_CAMPAIGN_5000.md). [Lessons from VirtualTissue-LN](docs/LN_REVIEW.md) informed event chapters and the static publication package. These additions preserve the calibrated simulation kernel.

The prepared repository includes the selected replay in `site/`. Serve that folder with any static web server to inspect the tissue without raw inputs, Python simulation or an inference key. See [upload and Pages instructions](docs/GITHUB_RELEASE.md) for the locally prepared release; no publication was performed by the recorder.

A Xenium-initialized atlas and individual-cell simulation for one human lung adenocarcinoma section. Explore measured B26/B27 polygons, competing cell annotations and pathway signatures, then follow autonomous cells through declared mechanical and biological programs.

**Version 0.2.1 adds structural compression constraints derived from the measured nucleus/cell area ratios and a persistent whole-campaign Jev budget.** It retains moving cells, reaction–diffusion fields, gated programs, wake scheduling, recorded comparisons and offline replay. New experiments use `contracts/runtime-v2-calibrated.json`; the original contracts and recordings remain available. The live smoke test validated 20 questions in one request. See [calibration and limits](docs/CALIBRATION.md), [campaign results](docs/CALIBRATION_RESULTS.md), the [autonomous runtime](docs/AUTONOMOUS_RUNTIME.md) and [verification](docs/VERIFICATION.md). Structural calibration does not identify patient kinetics or treatment response.

## What is available

- B26: 1,000 ROI cells, 2,883 internal contacts, 19 CD8–tumor contacts and 441 context objects.
- B27: 1,000 ROI cells, 2,975 internal contacts, 183 CAF–tumor contacts and 328 context objects. The v0.2 context has a fixed outer ring and a mechanically active interior; it does not acquire autonomous programs.
- Exact segmentation polygons; both annotations; all 20 observed signatures with missingness and depth residuals; a cell inspector with complete condition reports.
- A timed CD8 contact → damage → conditional death → macrophage clearance circuit with finite material, explicit identity/recognition assumptions and negative controls.
- Local-policy experiments, automatic private recordings, cell-level decision histories and saved-state replay.
- A bounded Jev recorder, tested with synthetic transport, a live smoke batch and the completed 72 h B26 campaign. The browser never makes paid inference calls.
- Moving power cells with crowding-limited division; CD8 migration, finite pulses, exhaustion and helped expansion; macrophage clearance and secretion; stromal matrix and cytokines; connected sprout perfusion and declared CD8 influx.
- Oxygen, glucose, lactate, VEGF-like, CXCL9/10-like, IFNγ-like, TGFβ-like, matrix and optional NE/CGRP-like fields. These are dimensionless SIM states, not measured concentrations.
- S0–S8 experiments, recognition-off and exactly static controls; per-cell wake reasons and daily decision caps; comparison at recorded times and a private standalone HTML player.

The supplied biological manual and reference rulebook are preserved. Operational corrections are versioned separately; read [the correction register](docs/CONTRACT_CORRECTIONS.md) before using historical example requests or eligibility counts. The original 20-run v0.2.0 campaign can be reproduced by adding `--contract contracts/runtime-v2.json` to the commands below; default new runs use the calibrated profile.

## Local setup

Python 3.12+ is required. Run commands from this folder. On Windows:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.lock
.venv\Scripts\python scripts/build_atlas.py --data-dir ..
.venv\Scripts\python scripts/build_atlas.py --data-dir .. --candidate 27
.venv\Scripts\python server.py --port 8026
```

On macOS/Linux use `.venv/bin/python` instead. A reproducible dependency snapshot is in `requirements.lock`; supported ranges are in `pyproject.toml`.

Open [the local studio](http://127.0.0.1:8026). The front page loads autonomous recordings and can run new local experiments. The [measured atlas and v0.1 contact laboratory](http://127.0.0.1:8026/atlas) remain accessible from its header. After setup, Windows users can also run `Start Studio.cmd`. The server binds only to loopback and uses no external fonts, scripts or graphics services.

The data directory must contain `LUAD3_TLS_GO20_UCell.h5ad` and `cell_boundaries.csv`. Raw inputs are not included in the release. The builder checks the source H5AD fingerprint and writes only under `outputs/`. See [data and provenance](docs/DATA.md).

## Use the studio

Load a recorded autonomous experiment, press **Play replay**, choose a field overlay, or seek to a recorded time. Click a polygon to inspect the cell's recorded state, permitted options, probabilities and wake reasons. **Compare with** adds a second tissue and trajectory from the same measured region. **Save view** saves a captioned PNG under `outputs/views/` (a download in the portable player). Playback makes no inference calls.

**Next frame**, **Final state** and the recorded event chapters navigate the saved experiment. A chapter is disabled when its event never occurred. Event time and saved-frame time are distinguished; chapters do not imply additional simulated states between frames.

Expand **Run a new local experiment**, choose B26/B27, scenario and seed, and create an experiment. Advance one modeled hour or run to 72 h; pause between saved hours. These controls use the declared local policy. The optional paid recorder is available only from the terminal with an explicit cap.

### Measured atlas and original contact laboratory

Choose a region and a color layer. Click a polygon or search for a cell ID. Cell 95048 in B26 illustrates the difference between T-lineage agreement and CD8 competence: one annotation calls it CD8 and the other CD4. Signature maps distinguish missing values from zero; changing a display layer changes no biology.

Choose a scenario, set a seed and create an experiment. `+10 min` advances one modeled clock step; `Run` continues to the six-hour horizon and can be paused. The default conservative baseline may remain quiet. The cognate scenario explicitly assigns recognition and uses primary-annotation competence. Checkpoint scenarios use a declared toy damage multiplier.

Every step is automatically saved to a unique file in `outputs/runs/`. `Export episode` downloads the current compressed record. `Open replay` verifies a saved record and displays its frames and decisions using the matching atlas. Replay does not recompute biology or call Jev. Old runs remain saved when a new experiment starts.

## Reproduce local controls

```powershell
.venv\Scripts\python scripts/validate_bundle.py --strict
.venv\Scripts\python -m pytest -q
.venv\Scripts\python scripts/verify_episodes.py
node --check web/app.js
```

The test suite uses synthetic decision providers and small artificial tissues. Additional tests verify real polygons and contact graphs when local atlas outputs exist. The episode checker runs five scenarios on each available region and saves an aggregate report and example cognate episodes under `outputs/`. It uses no API key.

### Reproduce the compression-calibrated v0.2.1 controls

```powershell
.venv\Scripts\python scripts/run_autonomous.py --scenarios S1,S2,static,recognition_off --seeds 21 --hours 72 --out outputs/calibrated-final
.venv\Scripts\python scripts/run_autonomous.py --atlas outputs/atlas_B27.json.gz --scenarios S1 --seeds 21 --hours 72 --out outputs/calibrated-final
.venv\Scripts\python scripts/verify_autonomous.py --directory outputs/calibrated-final
.venv\Scripts\python scripts/verify_calibration.py --directory outputs/calibrated-final
```

These commands use the new profile. The five completed controls and two 6 h sensitivity checks are documented in [calibration results](docs/CALIBRATION_RESULTS.md). Place accepted recordings in `outputs/calibrated-release/` to expose them in the studio; the release keeps the original recordings separately.

### Reproduce the original autonomous v0.2.0 experiments

```powershell
.venv\Scripts\python scripts/run_autonomous.py --contract contracts/runtime-v2.json --scenarios static,S0,S1,S2,S3,S4,S5,S6,S7,S8,recognition_off --seeds 21 --hours 72 --out outputs/autonomous-release
.venv\Scripts\python scripts/run_autonomous.py --contract contracts/runtime-v2.json --scenarios S1,S2,S5 --seeds 7,37 --hours 72 --out outputs/autonomous-release
.venv\Scripts\python scripts/run_autonomous.py --contract contracts/runtime-v2.json --atlas outputs/atlas_B27.json.gz --scenarios S0,S1,S4 --seeds 21 --hours 72 --out outputs/autonomous-release
.venv\Scripts\python scripts/verify_autonomous.py
.venv\Scripts\python scripts/export_player.py outputs/autonomous-release/LUAD3_B26-S1-seed21-72h-local.luad2.json.gz --output outputs/B26-offline-player.html
```

The exporter embeds the matching atlas and recorded frames into one HTML file. Open it directly in a browser without a server, internet or key. It contains private per-cell data and is excluded from the public release. The aggregate comparison is written to `outputs/autonomous-release/RESULTS.md`. The completed 20-run campaign is summarized in [results](docs/RESULTS.md), including matched controls, seed variability and mechanical limitations.

For B27 add `--atlas outputs/atlas_B27.json.gz`. Available scenarios and every numerical assumption are in `contracts/runtime-v2.json`. [The runtime guide](docs/AUTONOMOUS_RUNTIME.md) explains the model, its controls and limitations.

### Preserved M1 mechanics exercise

The original M1-only exercise remains reproducible separately. It provides moving power-diagram cells, pressure mechanics, self-propelled CD8 motility and tumor division under an exercise policy, without biological handlers or inference. It is a geometry control, not the autonomous runtime.

```powershell
.venv\Scripts\python scripts/run_v2_mechanics.py --hours 72 --scenarios static,m1_exercise
```

Outputs, including the t=0 fidelity report and private episodes, go to `outputs/v2/`. See the M1 section of [implemented scope](docs/IMPLEMENTATION.md).

To record one local experiment:

```powershell
.venv\Scripts\python scripts/record_experiment.py --scenario cognate --provider local --output outputs/my-cognate.luad.json.gz
```

## Optional live Jev recording

For v0.2, use a durable per-run journal and batched independent questions:

`python scripts/jev_smoke_b26.py` prepares one balanced batch of current kernel-validated B26 menus with zero calls. Its optional live mode requires both `--live` and an explicit `--max-requests` cap. It tests the protocol without applying returned actions to tissue.

```powershell
.venv\Scripts\python scripts/run_autonomous.py --scenarios S1 --seeds 21 --hours 72 --live --max-requests 100
```

This command first completes a local dry run and prints its request estimate. Its live trajectory may require a different number of requests. The cap covers the entire journal, including failed or uncertain requests. Use the same arguments plus `--resume` to reconstruct from the journal; known and uncertain paid requests are never sent again. HTTP errors and per-question repairs are audited. A replay is distinct from this deterministic reconstruction.

Review the local decision-concentration flags before a paid pilot. A single live M0 batch validated 20 questions; full campaign status is in [calibration results](docs/CALIBRATION_RESULTS.md). Use `scripts/run_jev_campaign.py` for a shared ceiling across smoke/pilot/final runs, rather than treating independent per-run caps as a global budget. Explicit paid intent, a cap and authorization for the external cellular-data payload are required. A protocol-valid response does not establish biological validity.

### Original v0.1 recorder

Only use this command when intending to make paid calls. Configure this project's `TYPESAFE_API_KEY` in the process environment without placing it in source, a browser form, recording or command-line argument. The program does not read sibling-project credentials or `.env` files.

```powershell
.venv\Scripts\python scripts/record_experiment.py --scenario cognate --provider jev --model jev-1.13.0 --max-requests 50 --output outputs/my-jev.luad.json.gz
```

The request limit includes failures and applies across the whole run. The recorder stops before an unaffordable decision round; reaching a limit produces a partial episode. A request budget is not a token or monetary budget. There is no automatic retry or silent local-policy replacement. Provider failures are logged, start no new programs, and do not erase previously committed physical events. The live smoke used the v0.2 batched adapter; this older v0.1 adapter has not been tested live.

## Project layout

| Path | Purpose |
|---|---|
| `src/luad_tissue/` | Reconstruction, condition evaluator, fixed-geometry engine, provider adapter and strict recording I/O |
| `contracts/` | Versioned operational assumptions and handler registry |
| `web/`, `server.py` | Local atlas, inspector, experiments and replay |
| `tests/` | Synthetic invariants, protocol/server checks and optional measured-data checks |
| `docs/` | English plan, implementation scope, corrections, provenance, verification and release guide |
| `MANUAL.md`, `rulebook/` | Unchanged supplied biological reference, templates and calibration |
| `data/` | Supplied aggregate reference tables; not required by the runtime |
| `examples/` | Supplied per-cell exploratory examples; ignored by Git and excluded from the public export |
| `scripts/` | Builders, recorder, verification, release packaging and preserved reference utilities |
| `outputs/` | Private generated atlases, audits and episodes; ignored by Git |

The original bundle README is preserved at [docs/reference/BUNDLE_README.md](docs/reference/BUNDLE_README.md). Its relative links describe the original bundle layout; current operational instructions are above.

## Future GitHub repository

```powershell
.venv\Scripts\python scripts/package_release.py
```

This creates an allowlisted archive and SHA-256 manifest in `dist/`, excluding raw inputs, per-cell examples, atlases, private recordings, credentials and environments. No GitHub repository is created or published by this command. See [release preparation](docs/GITHUB_RELEASE.md) and [attribution/license status](NOTICE.md).
