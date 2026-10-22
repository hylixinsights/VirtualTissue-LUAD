#!/usr/bin/env python3
"""Project one cell's measured state into a Jev /v1/systemone request.

This is the only place where the rulebook meets the wire. The rulebook itself is
never transmitted: it supplies the vocabulary, the eligibility test and the
question text, and this script emits the small `state` object that Jev sees.

    python scripts/build_jev_state.py \
        --patch examples/patch_B26.json \
        --rulebook rulebook/rulebook.json \
        --templates rulebook/question_templates.json \
        --rule CD8_COGNATE_CONTACT_DEGRANULATION \
        --out examples/jev_request_cd8_contact.json

With --rule omitted, the script reports how many cells in the patch are
eligible for each rule, which is the number that drives the per-tick Jev budget.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TUMOUR = {"Tumor", "Tumor_proliferating"}
MAX_PARTNERS_IN_STATE = 5


def labels(cell: dict) -> set[str]:
    return {c["label"] for c in cell["identity"]["candidates"]}


def lineages(cell: dict) -> set[str]:
    return {c.get("lineage") for c in cell["identity"]["candidates"]}


def identity_ok(cell: dict, accepted: list[str], policy: str, lineage_of: dict) -> bool:
    """Apply the rule's identity-conflict policy (rulebook.annotation.identity_conflict_policies).

    require_all_candidates_in_lineage -- every candidate label must map to a lineage the
        rule accepts. This is H15 applied strictly and is the default for irreversible or
        damaging actions: a cell called T_CD8 by one column and B_cell by the other may not
        kill anything.
    allow_any_candidate_match -- one matching candidate suffices; the state still carries
        identity_agreement so the model can weigh the uncertainty.
    """
    accepted_lineages = {lineage_of.get(a) for a in accepted} - {None}
    if policy == "require_all_candidates_in_lineage":
        cand = lineages(cell) - {None}
        return bool(cand) and cand <= accepted_lineages
    return bool(set(accepted) & labels(cell))


def eligible_for(rule: dict, cell: dict, by_id: dict, lineage_of: dict) -> list[dict]:
    """Return the contact partners (or [{}] for non-contact rules) that satisfy
    every condition the patch can actually evaluate.

    Conditions whose measurability is unobservable_by_design or assumed_only are
    NOT silently treated as satisfied. They are collected and reported, so the
    caller can see that the rule is spatially eligible but evidence-incomplete.
    """
    if not identity_ok(cell, rule["eligible_identities"],
                       rule.get("identity_conflict_policy", "allow_any_candidate_match"),
                       lineage_of):
        return []
    if cell["latent"]["viability_state"] not in ("alive", "assumed_alive"):
        return []

    conds = rule["required_conditions"].get("all", [])
    needs_contact = any(c["path"].startswith("contact.") or c["path"].startswith("target.")
                        for c in conds)
    gene_conds = [c for c in conds if c["path"] == "cell.genes_detected"]
    for c in gene_conds:
        det = set(cell["genes_detected"])
        if c["op"] == "contains" and c["value"] not in det:
            return []
        if c["op"] == "contains_any" and not (set(c["value"]) & det):
            return []
    for c in conds:
        if c["path"] == "cell.identity.agreement" and c["op"] == "eq":
            if cell["identity"]["agreement"] != c["value"]:
                return []

    if not needs_contact:
        return [{}]

    target_types = None
    for c in conds:
        if c["path"] == "target.identity.canonical_type" and c["op"] == "in":
            target_types = set(c["value"])
    max_gap = 1.0
    for c in conds:
        if c["path"] == "contact.polygon_gap_um" and c["op"] == "lte":
            max_gap = float(c["value"])

    out = []
    for contact in cell["contacts"]:
        if contact.get("occluded"):
            continue                       # no identity, no repertoire, never a target
        if contact["gap_um"] > max_gap:
            continue
        partner = by_id.get(contact["cell_id"])
        if partner is None:
            continue                       # outside the patch; engine must widen the window
        if target_types is not None and not identity_ok(
                partner, sorted(target_types),
                rule.get("target_conflict_policy", "allow_any_candidate_match"), lineage_of):
            continue
        tgt_gene_ok = True
        for c in conds:
            if c["path"] == "target.genes_detected":
                det = set(partner["genes_detected"])
                if c["op"] == "contains" and c["value"] not in det:
                    tgt_gene_ok = False
                if c["op"] == "contains_any" and not (set(c["value"]) & det):
                    tgt_gene_ok = False
        if tgt_gene_ok:
            out.append({"contact": contact, "partner": partner})
    return out


def unresolved_conditions(rule: dict) -> list[dict]:
    return [
        {"path": c["path"], "measurability": c["measurability"]}
        for c in rule["required_conditions"].get("all", [])
        if c["measurability"] in ("unobservable_by_design", "assumed_only")
    ]


def describe_identity(cell: dict) -> str:
    parts = [f"{c['label']} ({c['source']})" for c in cell["identity"]["candidates"]]
    return " / ".join(parts)


def project_state(cell: dict, rule: dict, hit: dict, patch: dict, rulebook: dict,
                  allowed: list[str], excluded: dict, perturbations: list[str]) -> dict:
    """Build the `state` object. Obeys jev.state_projection: nothing enters
    without its provenance, and no raw signature value travels without its
    percentile and coverage flag."""
    partner = hit.get("partner")
    contact = hit.get("contact")

    modulator_sigs = set()
    for mod in rule.get("conditional_modulators", []):
        if "hypoxia" in mod:
            modulator_sigs.add("GOBP_RESPONSE_TO_OXYGEN_LEVELS")
        if "energetic" in mod:
            modulator_sigs.add("GOBP_RESPONSE_TO_OXIDATIVE_STRESS")
        if "tgfb" in mod:
            modulator_sigs.add("GOBP_RESPONSE_TO_TRANSFORMING_GROWTH_FACTOR_BETA")

    sigs = {}
    for name in sorted(modulator_sigs):
        s = cell["signatures"].get(name)
        if s:
            sigs[name] = {
                "percentile_within_type": s["percentile_within_type"],
                "coverage_flag": s["coverage_flag"],
                "caveat": "rank within this cell type only; not an activation level",
            }

    named_genes = set()
    for c in rule["required_conditions"].get("all", []):
        if c["path"].endswith("genes_detected"):
            named_genes |= set(c["value"]) if isinstance(c["value"], list) else {c["value"]}
    genes = {g: ("observed" if g in cell["genes_detected"] else "not_detected")
             for g in sorted(named_genes)}
    for g in rulebook["panel"]["notable_absent"]:
        if g in named_genes:
            genes[g] = "not_assayed"
    flags = {g: cell["gene_flags"][g] for g in genes if g in cell.get("gene_flags", {})}

    state = {
        "cell": {
            "id": cell["cell_id"],
            "identity_candidates": [f"{c['label']} ({c['source']})" for c in cell["identity"]["candidates"]],
            "identity_agreement": cell["identity"]["agreement"],
            "detected_genes": cell["qc"]["n_genes_by_counts"],
            "depth_decile_within_type": cell["qc"]["depth_decile_within_type"],
            **({"genes": genes} if genes else {}),
        },
        "region": {
            "tls_candidate": cell["region"]["geodesic_candidate_id"],
            "in_lymphoid_core": bool(cell["region"]["is_candidate_core"] == 1),
            "tls_stage_name": cell["region"]["tls_stage_name"],
            "tls_stage_caveat": "delivered label, uncorroborated by any transcriptional correlate",
            "dist_to_nearest_tumor_core_um": cell["region"]["dist_to_nearest_tumor_core_um"],
            "dist_to_nearest_lymphoid_core_um": cell["region"]["dist_to_nearest_lymphoid_core_um"],
        },
        "contacts": {
            "definition": "polygon boundary gap <= 1.0 um; the tissue is fully packed",
            "n": len(cell["contacts"]),
            "partners": [],
        },
        "engine": {
            "eligibility_checked": True,
            "allowed_actions": allowed,
            "excluded_actions_with_reason": excluded,
            "decision_horizon": "one_exploratory_decision_step",
            "biological_duration": None,
            "quantitative_effect_execution_enabled": False,
        },
        "interpretation": {
            "probability_meaning": "relative_model_judgment_not_a_calibrated_event_rate",
            "assumed_competence_profile": "none",
            "active_perturbations": perturbations or ["none"],
            "unresolved_conditions": unresolved_conditions(rule),
        },
    }

    partners = []
    for c in sorted(cell["contacts"], key=lambda e: -e["interface_um"])[:MAX_PARTNERS_IN_STATE]:
        if c.get("occluded"):
            partners.append({"type_candidates": ["occluded_neighbour"],
                             "interface_um": c["interface_um"],
                             "note": "segmented but QC-dropped: occupies space, no identity"})
            continue
        p = None
        for cell2 in patch["cells"]:
            if cell2["cell_id"] == c["cell_id"]:
                p = cell2
                break
        partners.append({
            "type_candidates": sorted(labels(p)) if p else ["outside_patch"],
            "identity_agreement": p["identity"]["agreement"] if p else "unknown",
            "interface_um": c["interface_um"],
        })
    state["contacts"]["partners"] = partners
    if len(cell["contacts"]) > MAX_PARTNERS_IN_STATE:
        state["contacts"]["partners_omitted"] = len(cell["contacts"]) - MAX_PARTNERS_IN_STATE

    if sigs:
        state["cell"]["signature_ranks"] = sigs
    if flags:
        state["cell"]["gene_flags"] = flags
    if partner is not None:
        state["target"] = {
            "id": partner["cell_id"],
            "identity_candidates": [f"{c['label']} ({c['source']})" for c in partner["identity"]["candidates"]],
            "identity_agreement": partner["identity"]["agreement"],
            "interface_um": contact["interface_um"],
            "gap_um": contact["gap_um"],
            "viability_state": partner["latent"]["viability_state"],
        }
    return state


def fill(text: str, cell: dict, hit: dict, perturbations: list[str]) -> str:
    partner = hit.get("partner")
    contact = hit.get("contact")
    repl = {
        "{{cell_type_candidates}}": describe_identity(cell),
        "{{n_contacts}}": str(len(cell["contacts"])),
        "{{target_type_candidates}}": describe_identity(partner) if partner else "n/a",
        "{{interface_um}}": f"{contact['interface_um']:.1f}" if contact else "n/a",
        "{{dist_tumor_um}}": f"{cell['region']['dist_to_nearest_tumor_core_um']:.1f}",
        "{{dist_lymphoid_um}}": f"{cell['region']['dist_to_nearest_lymphoid_core_um']:.1f}",
        "{{horizon}}": "one decision step",
        "{{perturbation_list}}": ", ".join(perturbations) if perturbations else "none",
    }
    for k, v in repl.items():
        text = text.replace(k, v)
    return text


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--patch", required=True, type=Path)
    ap.add_argument("--rulebook", required=True, type=Path)
    ap.add_argument("--templates", required=True, type=Path)
    ap.add_argument("--rule", default=None)
    ap.add_argument("--cell-id", type=int, default=None)
    ap.add_argument("--perturbation", action="append", default=[])
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    patch = json.loads(args.patch.read_text(encoding="utf-8"))
    rb = json.loads(args.rulebook.read_text(encoding="utf-8"))
    qt = json.loads(args.templates.read_text(encoding="utf-8"))
    by_id = {c["cell_id"]: c for c in patch["cells"]}
    rules = {r["rule_id"]: r for r in rb["rules"]}
    lineage_of = {}
    for col, mapping in rb["annotation"]["lineage_map"].items():
        lineage_of.update(mapping)

    if args.rule is None:
        print(f"{patch['patch_id']}: {len(patch['cells'])} cells\n")
        print(f"{'rule':<40} {'eligible cells':>14} {'eligible interfaces':>20}")
        total = 0
        for rid, rule in rules.items():
            if not rule.get("enabled_by_default", True):
                print(f"{rid:<40} {'-':>14} {'(off by default)':>20}")
                continue
            cells = 0
            ifaces = 0
            for cell in patch["cells"]:
                hits = eligible_for(rule, cell, by_id, lineage_of)
                if hits:
                    cells += 1
                    ifaces += len(hits)
            total += cells
            print(f"{rid:<40} {cells:>14} {ifaces:>20}")
        print(f"\nupper bound on Jev calls per tick (one request per cell with any "
              f"eligible rule): <= {total}")
        print("Gate further: a cell whose admissible set has one option needs no call.")
        return

    rule = rules[args.rule]
    template_name = rule["jev_question_template"]
    template = qt["templates"][template_name]

    chosen = None
    for cell in patch["cells"]:
        if args.cell_id is not None and cell["cell_id"] != args.cell_id:
            continue
        hits = eligible_for(rule, cell, by_id, lineage_of)
        if hits:
            chosen = (cell, hits[0])
            break
    if chosen is None:
        sys.exit(f"no cell in {patch['patch_id']} is eligible for {args.rule}")

    cell, hit = chosen
    question = json.loads(json.dumps(template["question"]))
    question["instructions"] = fill(question["instructions"], cell, hit, args.perturbation)

    allowed = (list(question["criteria"]) if isinstance(question["criteria"], dict)
               else [f"level_{i}" for i in range(len(question["criteria"]))])
    # Actions the engine removed from the candidate set, each with its reason, so a
    # reviewer can tell an implausible action from one that was never offered.
    excluded = {}
    for c in unresolved_conditions(rule):
        if c["measurability"] == "unobservable_by_design":
            excluded[c["path"]] = ("unobservable_by_design: supplied by scenario, "
                                   "never inferred from RNA")
    forbidden = rb["capabilities"].get(rule["capability"], {}).get(
        "forbidden_evidence_substitutions", [])
    if forbidden:
        excluded["forbidden_evidence_substitutions"] = forbidden

    state = project_state(cell, rule, hit, patch, rb, allowed, excluded, args.perturbation)

    request = {
        "model": rb["jev"]["model"],
        "state": state,
        "questions": {template["question_key"]: question},
    }
    blob = json.dumps(request, indent=1)
    approx_tokens = len(blob) // 4
    cap = rb["jev"]["state_projection"]["hard_cap_tokens"]
    if approx_tokens > cap:
        sys.exit(f"projected state is ~{approx_tokens} tokens, over the {cap}-token cap")

    meta = {
        "_comment": "Generated by scripts/build_jev_state.py. POST the `model`, "
                    "`state` and `questions` keys to https://api.typesafe.ai/v1/systemone "
                    "with an Authorization: Bearer header. The keys below the underscore "
                    "are local audit context and must be stripped before sending.",
        "_rule_id": rule["rule_id"],
        "_rulebook_version": rb["rulebook_version"],
        "_patch_id": patch["patch_id"],
        "_cell_id": cell["cell_id"],
        "_approx_state_tokens": approx_tokens,
        "_target_tokens": rb["jev"]["state_projection"]["target_tokens"],
    }
    doc = {**meta, **request}

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
        print(f"wrote {args.out}  (~{approx_tokens} tokens of state)")
    else:
        print(json.dumps(doc, indent=1))


if __name__ == "__main__":
    main()
