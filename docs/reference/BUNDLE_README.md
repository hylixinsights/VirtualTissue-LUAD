# LUAD virtual tissue

A cell-level rulebook for running per-cell micro-decisions inside a real human lung adenocarcinoma section, with a TypeSafe **Jev** System One model as the judgement layer.

The sample is one 10x Xenium section: 133,464 annotated cells, 150,055 segmentation polygons, a 302-gene panel, twenty GO:BP signatures scored with pyUCell, and 28 tertiary-lymphoid-structure candidates. The simulation runs on a 1,000-cell patch containing a lymphoid follicle abutting a tumour nest.

**[MANUAL.md](MANUAL.md)** is the document to read. This file is the quick start.

---

## What's here

| Path | What it is |
| --- | --- |
| `MANUAL.md` | The rulebook in prose, with every measurement, its provenance and its limits, plus references |
| `rulebook/rulebook.json` | The same content, machine-readable. Read by the engine; **never sent to Jev** |
| `rulebook/calibration.json` | Reference distributions that turn a raw pathway score into a percentile and a depth residual. Generated |
| `rulebook/question_templates.json` | Ready-made Jev `questions` blocks, one per decision domain |
| `rulebook/*.schema.json` | JSON Schema 2020-12 for each of the three |
| `examples/patch_B26.json` | The reference patch: 1,000 cells, 324 × 321 µm, with contacts, signatures and identity |
| `examples/jev_request_*.json` | Three worked `/v1/systemone` requests |
| `scripts/` | Everything that generated the above, plus the bundle validator |

## Quick start

```bash
pip install h5py numpy pandas scipy shapely 'jsonschema>=4.18'

# 1. fit the reference distributions on the whole section
python scripts/build_calibration.py \
    --h5ad LUAD3_TLS_GO20_UCell.h5ad \
    --out rulebook/calibration.json

# 2. cut the simulation patch
python scripts/export_patch.py \
    --h5ad LUAD3_TLS_GO20_UCell.h5ad \
    --boundaries cell_boundaries.csv \
    --calibration rulebook/calibration.json \
    --candidate 26 --n-cells 1000 \
    --out examples/patch_B26.json

# 3. check the bundle is internally consistent (run this in CI)
python scripts/validate_bundle.py

# 4. see how many cells are eligible for each rule
python scripts/build_jev_state.py \
    --patch examples/patch_B26.json \
    --rulebook rulebook/rulebook.json \
    --templates rulebook/question_templates.json

# 5. build one request
python scripts/build_jev_state.py \
    --patch examples/patch_B26.json \
    --rulebook rulebook/rulebook.json \
    --templates rulebook/question_templates.json \
    --rule CD8_COGNATE_CONTACT_DEGRANULATION \
    --out examples/jev_request_cd8.json
```

Then `POST` the `model`, `state` and `questions` keys of that file to `https://api.typesafe.ai/v1/systemone` with an `Authorization: Bearer` header. The keys prefixed with `_` are local audit context and are stripped before sending.

## How the pieces fit

```
engine                      rulebook.json            Jev
──────                      ─────────────            ───
owns geometry, contacts,    which actions exist,     ranks admissible
fields, timers, cycle,      who may take them,       behaviours and
damage, death, audit        what gates them,         returns a calibrated
                            what is measured         distribution
        │                          │                      │
        └──── projects a ~900-token `state` per decision ──┘
                   (the rulebook itself never travels)
```

Three layers, and the separation is the point. Jev is never asked whether a cell dies, whether it divides, or what it is. It ranks options that code has already validated, and its option probability is a model preference, not an event rate.

## Three things to know before using this

**Contact is measured, not approximated.** Two cells are in contact when their segmentation polygons come within 1 µm. A centroid-distance threshold reaches only F1 0.658 against that graph and is biased by cell size in opposite directions for large and small cells, so it is forbidden. The tissue is a near-complete tiling — mean 6.11 contacts per cell, essentially the whole perimeter abutting a neighbour — so movement and division must displace, never occupy void.

**A raw pathway score is not a state variable.** It tracks detection depth, with ρ up to 0.81 *within* a single cell type. Only a percentile within cell type and depth decile may enter a rule. No signature in this panel has both adequate gene coverage and freedom from lineage-identity confounding.

**Identity is a set.** The two annotations shipped with the object agree exactly on 34.9 % of cells and at lineage level on 62.6 %; the gap is vocabulary, and conflating the two freezes whole compartments for the wrong reason. Rules declare whether they need all candidate labels to agree or just one. The choice matters: the canonical CD8-kills-tumour rule is eligible for 29 cells in the reference patch under the permissive policy and **1** under the strict one.

## Perturbations

`hypoxia`, `angiogenesis`, `resistance_mutation`, `checkpoint_blockade`, `inflammation`. Every one is a simulation construct. Each declares the state variables it adds, the rules it unlocks, what the sample can and cannot show about it, and a reporting requirement that follows into every figure.

The honest version of that: pO₂ was never measured, so the oxygen field carries no physical units; LUAD3 has no genotype metadata, so a resistance mutation is a declaration; `PDCD1` is detected in 0.6 % of CD8 cells, so the checkpoint axis is entirely scenario; and every cytokine receptor in the inflammation perturbation is absent from the panel.

## Status

`rulebook_version` 1.0.0. Twelve rules, ten question templates, ten calibrated cell types. `validate_bundle.py` exits 0.

Nothing here is calibrated to real time. Every `event_rate` is `null` and the schema refuses a non-null rate on an uncalibrated rule. Trajectories are scenarios, not predictions — see MANUAL.md §17.5 for what would change that.

## Citing

The sample is n = 1: one patient, one section, no replicate. Values labelled `D-LUAD3` describe this section and are the right basis for initialising a simulation. None of them estimates LUAD as a disease.
