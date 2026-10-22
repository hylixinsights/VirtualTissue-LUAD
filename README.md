# LUAD Tissue Studio

Repository: [hylixinsights/VirtualTissue-LUAD](https://github.com/hylixinsights/VirtualTissue-LUAD). The 30 September Jev campaign completed 72 modeled hours: 1,059 new requests, 1,060 cumulatively against the authorized 5,000 ceiling, and 17,071 individual decisions. See [the recorded campaign](docs/JEV_CAMPAIGN_5000.md). [Lessons from VirtualTissue-LN](docs/LN_REVIEW.md) informed event chapters and the static publication package. These additions preserve the calibrated simulation kernel.

The prepared repository includes the selected replay in `site/`. Serve that folder with any static web server to inspect the tissue without raw inputs, Python simulation or an inference key. See [upload and Pages instructions](docs/GITHUB_RELEASE.md) for the locally prepared release; no publication was performed by the recorder.

A Xenium-initialized atlas and individual-cell simulation for one human lung adenocarcinoma section. Explore measured B26/B27 polygons, competing cell annotations and pathway signatures, then follow autonomous cells through declared mechanical and biological programs.

**Version 0.2.1 adds structural compression constraints derived from the measured nucleus/cell area ratios and a persistent whole-campaign Jev budget.** It retains moving cells, reaction–diffusion fields, gated programs, wake scheduling, recorded comparisons and offline replay. New experiments use `contracts/runtime-v2-calibrated.json`; the original contracts and recordings remain available. The live smoke test validated 20 questions in one request. See [calibration and limits](docs/CALIBRATION.md), [campaign results](docs/CALIBRATION_RESULTS.md), the [autonomous runtime](docs/AUTONOMOUS_RUNTIME.md) and [verification](docs/VERIFICATION.md). Structural calibration does not identify patient kinetics or treatment response.

## Dataset provenance and credit

The experimental starting point is **one human lung adenocarcinoma section, locally identified as LUAD3, measured with the 10x Genomics Xenium platform**. Credit for collecting the specimen and generating the original experimental dataset belongs to the original investigators and data providers listed below. This repository contributes a tissue reconstruction, a rule-based simulation and a recorded experiment built from those observations.

**Documentation in progress:** `[add here this info]` marks information that could not be established from the supplied files. Replace each placeholder with the verified information; the surrounding field identifies what is needed. The filename `LUAD3` and the platform name do not identify an original publication or accession.

| Original dataset credit | Information |
|---|---|
| Dataset creators, contributing laboratories and institutions | [add here this info] |
| Full original dataset/publication citation, including DOI | [add here this info] |
| Official dataset URL, accession and release/version used | [add here this info] |
| Mapping of the local identifier LUAD3 to the original sample/slide identifier | [add here this info] |
| Specimen preparation and available clinical/histological description | [add here this info] |
| Xenium panel name/version, processing software and segmentation version/settings | [add here this info] |
| Dataset reuse terms and required acknowledgments | [add here this info] |

The supplied analysis object is `LUAD3_TLS_GO20_UCell.h5ad`, derived from `Xenium_LUAD_No3_annotated.h5ad`; `cell_boundaries.csv` supplies segmentation polygons. The analysis object contains **133,464 annotated cells and 302 genes**. The boundary file contains **150,055 polygons**, including objects without a matching retained annotated cell. Twenty signature scores are available for **44,134 cells** assigned to the 28 candidate regions. These are different denominators and should not be interchanged. Input hashes and reconstruction details are in [data provenance](docs/DATA.md).

The raw inputs are not included in this repository. The selected replay in `site/` does contain derived per-cell geometry, annotations and recorded observations; it is not an anonymized or aggregate-only dataset. Credit to the source investigators applies to these derivatives as well.

## How the cells were annotated

The simulation imports annotations already present in the supplied AnnData object. It does not perform a new cell-type annotation, and Jev does not assign cell identities. The available object establishes the following relationships between the annotation columns; the upstream methods still need to be completed:

| Annotation field | What is documented | Method to complete |
|---|---|---|
| `first_type` | A separate annotation vocabulary; the upstream GO-score delivery calls this its primary annotation. | Annotation method, reference atlas or marker panel, software/model version and parameters: [add here this info] |
| `leiden` and `cell_type` | The same ten-group partition is stored as cluster IDs and cell-type labels. | Expression preprocessing, feature selection, software versions and cluster-to-type labeling criteria: [add here this info] |
| `cell_type_fine` | Refines `cell_type` within the T-cell compartment: 3,756 labels change from CD4 to cytotoxic CD8 and 91 in the reverse direction. This is the first identity candidate used in the simulation atlas and the label source for the patch counts below. | CD4/CD8 refinement method, marker thresholds, supporting reference and manual corrections: [add here this info] |

The stored `uns['leiden']['params']` records `resolution=1.0`, `random_state=0` and `n_iterations=2`. The stored `uns['neighbors']['params']` records `n_neighbors=10`, `n_pcs=30`, `metric='euclidean'`, `method='umap'` and `random_state=0`. These metadata do not establish the complete preprocessing or manual labeling workflow, and they are not evidence for the graph settings used in spatial TLS detection.

Upstream quality-control thresholds and filtering steps: [add here this info]. The expression layer `purified_raw` is described in the supplied provenance as **SPLIT-corrected**; the SPLIT implementation, citation, version and parameters are: [add here this info]. Annotation contributors and independent/manual validation are: [add here this info].

Both `cell_type_fine` and `first_type` are retained for each annotated cell. The atlas records exact agreement, agreement after lineage mapping, or a conflict. Different vocabularies are not automatically treated as biological disagreement, and conflicting labels are not silently replaced. Physical objects without an annotation remain present as context objects without autonomous programs. The identity assumptions of a simulation scenario are recorded separately from these measured labels; see [the identity audit](MANUAL.md#4-cell-identity-is-a-set-not-a-label) and [operational corrections](docs/CONTRACT_CORRECTIONS.md).

Cell IDs join annotations to segmentation polygons. `obsm['spatial']` contains coordinates in micrometres aligned with the boundary file; the source's X-mirrored coordinates are retained in `obsm['spatial_original']` and are not used for this reconstruction.

## How TLS candidates were identified

The supplied analysis contains **28 geodesic TLS candidate regions**, imported from the upstream `tissue_candidate_assignment.csv` by `cell_id`. The H5AD retains `geodesic_candidate_id` and `is_candidate_core`, as well as `TLS_stage`, `TLS_stage_name` and `TLS_class`. The virtual-tissue builder consumes these assignments; it does not rediscover TLS from a simulated trajectory.

The candidate regions contain **18,879 core cells and 25,255 surrounding cells**. All delivered core cells are labeled `B_cell` under `first_type`. This describes the supplied mask and is not independent validation of a B-cell-rich structure. The full detection procedure cannot be recovered from the resulting masks alone:

| Upstream TLS analysis step | Details to complete |
|---|---|
| Candidate-core detection | Cell labels/markers used, algorithm, thresholds and minimum size: [add here this info] |
| Neighborhood graph and geodesic expansion | Edge definition, distance metric, expansion limits and handling of overlapping regions: [add here this info] |
| Tumor-core annotation | Method and thresholds used to identify the tumor cores associated with the TLS analysis: [add here this info] |
| TLS stage assignment and independent validation | Criteria for early aggregate, primary follicle and mature labels; histology, staining or expert review, if performed: [add here this info] |
| Analysis provenance and credit | Contributors, software versions and source scripts/notebooks: [add here this info] |

The delivered `TLS_stage_name` labels comprise **12 mature, 15 primary-follicle and one early-aggregate core**. These remain supplied architectural labels. `TLS_stage` and `TLS_stage_name` are not interchangeable encodings in this object. The simulation records maturity as `delivered_label_uncorroborated`; these labels alone do not establish a functional germinal center or authorize a cellular behavior. See [the TLS audit](MANUAL.md#7-tertiary-lymphoid-structures).

### How B26 was selected for the simulation

TLS detection and simulation-window selection are separate steps. After the 28 candidate cores had been supplied, windows of **1,000 annotated cells** around those cores were surveyed. For a selected candidate, the atlas builder takes the mean of its core-cell spatial coordinates and selects the 1,000 nearest annotated cells from the section. It then reconstructs the selected cells' polygons and their contacts. A measured contact is defined by a polygon-to-polygon gap of **at most 1 µm**; a nearby centroid alone is not a contact.

**B26 was chosen for the TLS–tumor interface experiment:** its approximately **324 × 321 µm** window contains a supplied primary-follicle core next to a tumor nest, with **19 CD8–tumor contact pairs involving 10 distinct CD8 cells**. **B27** is the secondary window for tumor–stroma questions because it contains **183 CAF–tumor contacts**.

| Initial 1,000-cell simulation window | B26 | B27 |
|---|---:|---:|
| B cells | 381 | 155 |
| Cytotoxic CD8 labels | 205 | 73 |
| Tumor labels, including proliferating tumor | 139 | 236 |
| CD8–tumor contact pairs | 19 | 2 |
| CAF–tumor contact pairs | 45 | 183 |

These windows are not the complete geodesic candidate regions: the upstream B26 region contains 1,104 cells and B27 contains 576, whereas each simulation ROI contains 1,000 cells selected around its core. An additional 30 µm polygon halo preserves boundary context, adding 441 objects for B26 and 328 for B27 outside the ROI denominator. Context objects remain distinct from autonomous ROI cells. Selection was designed to study particular interfaces; these windows are not an unbiased sample of the whole section. The measurements and scan are documented in [the patch specification](MANUAL.md#11-the-simulation-patch) and [the atlas builder](src/luad_tissue/atlas.py).

## Pathway signatures and method attribution

The supplied score analysis used **20 human MSigDB 2026.1.Hs C5:GO:BP gene sets**, selected for biological relevance and at least five panel genes before candidate scores were compared. The C5:GO:BP collection derives from the Gene Ontology Biological Process resource; see [MSigDB collections and acknowledgments](https://www.gsea-msigdb.org/gsea/msigdb/human/collections.jsp#C5).

Scores were computed with **pyUCell 0.7.3** on `purified_raw`, using `max_rank=100`, `ties_method='average'` and `missing_genes='skip'`, on CPU, without smoothing or additional normalization. Each cell was ranked against the 302 panel genes; only the gene-set/panel intersection contributed. Unscored cells retain missing values rather than zero. These are rank-based signature scores, not enrichment p-values, NES values or measurements of pathway flux. The supplied manual documents panel coverage, cell-type confounding and detection-depth effects; [calibration](docs/CALIBRATION.md) describes their use and limitations in the simulation.

Please credit **Massimo Andreatta and Santiago J. Carmona** for [UCell (2021)](https://doi.org/10.1016/j.csbj.2021.06.043) and [UCell and pyUCell (2026)](https://doi.org/10.1093/bioinformatics/btag055), as specified in the [official pyUCell citation guidance](https://pyucell.readthedocs.io/en/latest/#citation). The supplied analysis documentation names `analysis/pathway_scores_go20.py` as the scoring entry point and `tmp/pathway_scores_go20/export_go20.mjs` as the table exporter. Contributors and the repository/commit containing those upstream scripts: [add here this info]. These method citations are separate from the original experimental dataset citation above.

Concept and biological direction are credited to **Helder Nakaya, CSBL / Hylix.app**, and implementation assistance to **OpenAI Codex**, as recorded in [NOTICE.md](NOTICE.md). Original data generation, upstream annotation and TLS analysis require their own contributor credits in the fields above. The supplied [biological manual](MANUAL.md) preserves the literature references used to formulate the simulation rules.

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
