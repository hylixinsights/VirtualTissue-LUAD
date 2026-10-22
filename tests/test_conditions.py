import copy
import pytest
from luad_tissue.conditions import aggregate, compare, identity_gate, cell_report
from conftest import make_cell


@pytest.mark.parametrize("actual,op,expected,result", [
    (None,"eq",True,"unknown"),(0,"eq",0,"true"),(False,"eq",True,"false"),
    ("concordant_lineage","in",["concordant_exact","concordant_lineage"],"true"),
    (["A"],"contains_any",["B"],"false"),(["A"],"contains","A","true"),
    (1.0,"lte",1.0,"true"),(2,"gte",3,"false"),(0,"neq",1,"true")])
def test_three_valued_operators(actual,op,expected,result):
    assert compare(actual,op,expected)==result


def test_unknown_operator_is_not_silently_ignored():
    with pytest.raises(ValueError):compare(1,"invented",1)


def test_subtype_disagreement_is_not_lineage_competence():
    cell=make_cell(1,"T_CD8_cytotoxic","T_CD4")
    assert not identity_gate(cell,["T_CD8_cytotoxic"])
    assert identity_gate(cell,["T_CD8_cytotoxic"],"primary_annotation")


def test_unknown_candidate_is_not_dropped():
    cell=make_cell(1,"T_CD8_cytotoxic")
    cell["identity"]["candidates"][1]=dict(label="unknown",lineage=None)
    assert not identity_gate(cell,["T_CD8_cytotoxic"])


def test_b_cell_is_not_promoted_to_plasma():
    cell=make_cell(1,"Plasma_cell","B_cell")
    assert identity_gate(cell,["Plasma_cell"])
    cell["identity"]["candidates"][0]["label"]="B_cell"
    assert not identity_gate(cell,["Plasma_cell"])


def test_plasma_in_condition_rejects_conflict(atlas,rulebook,contract):
    cell=make_cell(4,"Plasma_cell","Tumor")
    cell["identity"]["agreement"]="conflict"
    report=next(r for r in cell_report(cell,{4:cell},rulebook["rules"],contract,scenario=contract["scenarios"]["cognate"]) if r["rule_id"]=="PLASMA_CELL_SECRETION")
    assert next(c for c in report["checks"] if c["path"]=="cell.identity.agreement")["result"]=="false"


def test_missing_gene_is_unknown_not_negative(rulebook,contract):
    cell=make_cell(4,"Plasma_cell","B_cell")
    cell["genes_detected"]=[]
    cell["panel_genes"]=[]
    report=next(r for r in cell_report(cell,{4:cell},rulebook["rules"],contract) if r["rule_id"]=="PLASMA_CELL_SECRETION")
    assert next(c for c in report["checks"] if c["path"]=="cell.genes_detected")["result"]=="unknown"


def test_reference_and_runtime_are_separate(rulebook,contract):
    cell=make_cell(4,"Plasma_cell","B_cell")
    report=next(r for r in cell_report(cell,{4:cell},rulebook["rules"],contract) if r["rule_id"]=="PLASMA_CELL_SECRETION")
    assert report["reference_result"]=="true"
    assert report["result"]=="false"  # secretion has no handler yet
