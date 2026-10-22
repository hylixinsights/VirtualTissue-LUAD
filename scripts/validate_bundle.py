#!/usr/bin/env python3
"""Validate the rulebook bundle: JSON Schema plus the cross-references a schema cannot express.

    python scripts/validate_bundle.py           # validates rulebook/ in place
    python scripts/validate_bundle.py --strict  # warnings become failures

Exit code 0 means the bundle is internally consistent. This is the check to run
in CI on every pull request that touches rulebook/.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover
    sys.exit("pip install jsonschema")

ROOT = Path(__file__).resolve().parents[1]
RB = ROOT / "rulebook"

errors: list[str] = []
warnings: list[str] = []


def fail(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def load(name: str) -> dict:
    path = RB / name
    if not path.exists():
        fail(f"missing file: rulebook/{name}")
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def schema_check(doc: dict, schema_name: str, label: str) -> None:
    schema = load(schema_name)
    if not schema or not doc:
        return
    validator = Draft202012Validator(schema)
    for err in sorted(validator.iter_errors(doc), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in err.path) or "<root>"
        fail(f"[{label}] {loc}: {err.message}")


def cross_check(rb: dict, qt: dict, cal: dict) -> None:
    caps = set(rb.get("capabilities", {}))
    types = set(rb.get("cell_types", {}))
    domains = rb.get("decision_domains", {})
    templates = qt.get("templates", {})
    rules = {r["rule_id"]: r for r in rb.get("rules", [])}

    # cell types declare only capabilities that exist
    for t, spec in rb.get("cell_types", {}).items():
        for c in spec.get("capabilities", []):
            if c not in caps:
                fail(f"cell_types.{t} declares unknown capability '{c}'")

    for rid, rule in rules.items():
        if rule["capability"] not in caps:
            fail(f"rules.{rid}: unknown capability '{rule['capability']}'")
        for ident in rule["eligible_identities"]:
            if ident not in types:
                fail(f"rules.{rid}: unknown identity '{ident}'")
            else:
                declared = rb["cell_types"][ident].get("capabilities", [])
                if rule["capability"] not in declared:
                    fail(f"rules.{rid}: {ident} does not declare capability "
                         f"'{rule['capability']}' (a rule may not grant a capability "
                         f"the cell type does not have)")
        dom = rule["decision_domain"]
        if dom not in domains:
            fail(f"rules.{rid}: unknown decision_domain '{dom}'")
        elif domains[dom].get("engine_owned"):
            fail(f"rules.{rid}: decision_domain '{dom}' is engine-owned and may not carry a rule")

        # every condition path that is unobservable must not be the sole gate
        conds = rule["required_conditions"].get("all", []) + rule["required_conditions"].get("any", [])
        if conds and all(c["measurability"] == "unobservable_by_design" for c in conds):
            fail(f"rules.{rid}: every required condition is unobservable_by_design; "
                 f"the rule can never become eligible and should be marked enabled_by_default=false")
        if not conds:
            fail(f"rules.{rid}: no required conditions")

        tmpl = rule.get("jev_question_template")
        if tmpl is None:
            if rule.get("enabled_by_default", True):
                fail(f"rules.{rid}: enabled by default but has no jev_question_template")
        elif tmpl not in templates:
            fail(f"rules.{rid}: jev_question_template '{tmpl}' not found")
        else:
            t = templates[tmpl]
            if rid not in t["rule_ids"]:
                fail(f"question_templates.{tmpl}: does not list rule '{rid}' in rule_ids")
            if t["decision_domain"] != dom:
                fail(f"question_templates.{tmpl}: decision_domain '{t['decision_domain']}' "
                     f"!= rule {rid} domain '{dom}'")
            want = domains[dom].get("question_type")
            got = t["question"]["type"]
            if want and got != want:
                fail(f"question_templates.{tmpl}: question type '{got}' but domain "
                     f"'{dom}' declares '{want}'")

        # calibration_status and event_rate coherence (schema covers the null case)
        if rule["calibration_status"] == "calibrated" and rule["event_rate"] is None:
            fail(f"rules.{rid}: marked calibrated but event_rate is null")

    for tname, t in templates.items():
        for rid in t["rule_ids"]:
            if rid not in rules:
                fail(f"question_templates.{tname}: unknown rule '{rid}'")

    # perturbations point at real rules and never unlock an enabled-by-default rule
    for pname, p in rb.get("perturbations", {}).items():
        if pname.startswith("_"):
            continue
        for rid in p.get("unlocks_rules", []):
            if rid not in rules:
                fail(f"perturbations.{pname}: unlocks unknown rule '{rid}'")
            elif rules[rid].get("enabled_by_default", True):
                fail(f"perturbations.{pname}: unlocks '{rid}', which is already enabled by default")
        for rid in p.get("modulates_rules", []):
            if rid not in rules:
                fail(f"perturbations.{pname}: modulates unknown rule '{rid}'")

    # every rule that is off by default should be reachable through some perturbation
    unlocked = {rid for p in rb.get("perturbations", {}).values()
                if isinstance(p, dict) for rid in p.get("unlocks_rules", [])}
    for rid, rule in rules.items():
        if not rule.get("enabled_by_default", True) and rid not in unlocked:
            if "disabled_reason" not in rule:
                warn(f"rules.{rid}: disabled and not unlocked by any perturbation, "
                     f"and carries no disabled_reason")

    # engine constraint ids unique, and a superseded one is not cited as a live basis
    seen = set()
    for c in rb.get("engine_constraints", []):
        if c["id"] in seen:
            fail(f"engine_constraints: duplicate id {c['id']}")
        seen.add(c["id"])
        if c.get("supersedes") and c["supersedes"] not in seen | {x["id"] for x in rb["engine_constraints"]}:
            fail(f"engine_constraints.{c['id']}: supersedes unknown id {c['supersedes']}")

    # interactions marked complete must really have nothing missing (schema) and be counted
    complete = [k for k, v in rb.get("interactions", {}).items()
                if isinstance(v, dict) and v.get("status") == "complete"]
    declared = rb.get("interactions", {}).get("_summary", {}).get("n_fully_on_panel")
    if declared is not None and declared != len(complete):
        fail(f"interactions._summary.n_fully_on_panel = {declared} but {len(complete)} edges "
             f"are marked complete: {sorted(complete)}")

    # calibration agrees with the rulebook
    if cal:
        cal_types = set(cal.get("cell_types", {}))
        unknown = cal_types - types
        if unknown:
            fail(f"calibration: cell types absent from the rulebook: {sorted(unknown)}")
        missing = {t for t in types if rb["cell_types"][t].get("n_scored", 0) > 0} - cal_types
        if missing:
            warn(f"calibration: rulebook cell types with scored cells but no calibration: {sorted(missing)}")
        if cal.get("source", {}).get("annotation_column") != rb["annotation"]["primary_column"]:
            fail(f"calibration was fitted on '{cal.get('source', {}).get('annotation_column')}' "
                 f"but the rulebook primary annotation is '{rb['annotation']['primary_column']}'")
        for t, spec in cal.get("cell_types", {}).items():
            for sig, ref in spec.get("signatures", {}).items():
                if sig not in cal.get("signatures", {}):
                    fail(f"calibration.cell_types.{t}: unknown signature '{sig}'")
                edges = ref["percentile_edges"]
                if any(b < a for a, b in zip(edges, edges[1:])):
                    fail(f"calibration.cell_types.{t}.{sig}: percentile_edges are not monotone")
                if ref["coverage_flag"] != cal["signatures"].get(sig, {}).get("coverage_flag"):
                    fail(f"calibration.cell_types.{t}.{sig}: coverage_flag disagrees with the signature header")

    # version coherence
    if qt.get("rulebook_version") != rb.get("rulebook_version"):
        fail(f"question_templates.rulebook_version {qt.get('rulebook_version')} "
             f"!= rulebook_version {rb.get('rulebook_version')}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true", help="treat warnings as failures")
    args = ap.parse_args()

    rb = load("rulebook.json")
    qt = load("question_templates.json")
    cal_path = RB / "calibration.json"
    cal = json.loads(cal_path.read_text(encoding="utf-8")) if cal_path.exists() else {}
    if not cal:
        warn("rulebook/calibration.json not found; run scripts/build_calibration.py")

    schema_check(rb, "rulebook.schema.json", "rulebook")
    schema_check(qt, "question_templates.schema.json", "question_templates")
    if cal:
        schema_check(cal, "calibration.schema.json", "calibration")
    cross_check(rb, qt, cal)

    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")

    n_rules = len(rb.get("rules", []))
    n_tmpl = len(qt.get("templates", {}))
    n_types = len(cal.get("cell_types", {}))
    print(f"\n{n_rules} rules, {n_tmpl} question templates, "
          f"{n_types} calibrated cell types, "
          f"{len(errors)} errors, {len(warnings)} warnings")

    if errors or (args.strict and warnings):
        sys.exit(1)
    print("bundle OK")


if __name__ == "__main__":
    main()
