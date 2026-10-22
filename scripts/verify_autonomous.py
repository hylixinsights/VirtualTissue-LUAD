"""Validate completed recorded runs and write an aggregate comparison in English."""
import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from luad_tissue.io import read_json,write_json
from luad_tissue.v2.episode import validate_episode


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--directory",type=Path,default=ROOT/"outputs/autonomous-release")
    args = p.parse_args()
    rows = []
    atlases = {}
    grids = {}
    matched_initial_oxygen = {}
    for path in sorted(args.directory.glob("*.luad2.json.gz")):
        e = read_json(path)
        if e["summary"]["stop_reason"] != "horizon_reached":
            print(f"Partial recording retained, excluded from completed-run comparison: {path.name}")
            continue
        region = 27 if e["patch_id"].endswith("B27") else 26
        atlases.setdefault(region,read_json(ROOT/f"outputs/atlas_B{region}.json.gz"))
        validate_episode(e,atlases[region])
        grid = e["field_grid"]
        geometry = {key:grid[key] for key in ("origin_um","spacing_um","shape")}
        assert grids.setdefault(region,geometry) == geometry, "Scenario changed the field domain"
        if e["scenario"] in ("S1","S2","S5","S6","S7","S8","recognition_off"):
            key = (region,e["seed"])
            oxygen = e["frames"][0]["fields"]["oxygen"]
            assert matched_initial_oxygen.setdefault(key,oxygen) == oxygen, "Unmatched initial oxygen"
        s = e["summary"]
        acc = s["accounting"]
        assert sum(acc["acting"].values()) == acc["expected_acting_total"]
        assert acc["context_total"] == acc["expected_context_total"]
        by_day = Counter((d["cell_id"],d["time_min"]//1440) for d in e["decisions"])
        assert max(by_day.values(),default=0) <= e["contract"]["scheduler"]["max_per_cell_day"]
        assert all(d["observation"]["primary_label"] not in ("B_cell","Plasma_cell","occluded") for d in e["decisions"])
        if e["scenario"] in ("S0","recognition_off","static"):
            assert s["events"].get("cytotoxic_pulse",0) == 0
            assert s["events"].get("apoptosis_committed",0) == 0
        if e["scenario"] == "static":
            assert e["frames"][0]["x"] == e["frames"][-1]["x"]
            assert e["frames"][0]["y"] == e["frames"][-1]["y"]
            assert not e["events"] and not e["decisions"]
        assert s["final"]["field_balance_max"] < 1e-6
        assert s["final"]["field_residual_max"] < 1e-7
        dynamic_metrics = [f["metrics"] for f in e["frames"] if f["time_min"] > 0]
        assert max(m["field_balance_max"] for m in dynamic_metrics) < 1e-6
        assert max(m["field_residual_max"] for m in dynamic_metrics) < 1e-7
        report_path = path.with_name(path.name.replace(".luad2.json.gz",".report.json"))
        report = read_json(report_path)
        assert abs(report["overlap"]["relative_overlap"]) < 1e-8
        assert report["episode_fingerprint"] == e["fingerprint"]
        rows.append(dict(file=path.name,provider=e["provider"],region=region,scenario=e["scenario"],seed=e["seed"],hours=s["time_min"]/60,
                         tumor=s["final"]["tumour_cells"],kills=s["final"]["kills"],born=acc["born"],
                         recruited=acc["recruited"],hypoxic_fraction=s["final"]["hypoxic_tumour_fraction"],
                         exhaustion=s["final"]["cd8_exhaustion"],decisions=s["decisions"],calls_estimate=s["estimated_requests"],
                         paid_calls=s["paid_calls"],seconds=report["seconds"],invalid=s["invalid_answers"],
                         concentration_flag=s["decision_share_above_half"],fingerprint=e["fingerprint"],final_state_fingerprint=e["final_state_fingerprint"]))
        rows[-1].update(hidden=s["final"]["hidden"],pressure_mean=s["final"]["pressure_mean"],
                        perfused_new_length_um=s["final"]["perfused_vessel_length_um"],
                        sprout_length_um=s["final"]["vessel_length_um"],
                        field_balance_peak=max(m["field_balance_max"] for m in dynamic_metrics),
                        field_residual_peak=max(m["field_residual_max"] for m in dynamic_metrics))
        print(f"Verified {path.name}: tumor {rows[-1]['tumor']}, kills {rows[-1]['kills']}, {s['decisions']} decisions")
    if not rows: raise SystemExit("No completed autonomous recording available")
    write_json(args.directory/"verification.json",dict(format="luad-autonomous-verification",runs=rows,paid_calls=sum(r["paid_calls"] for r in rows)))
    lines = ["# Autonomous run comparison", "", "All numbers below describe declared simulation experiments, not observations or patient predictions. The provider and actual HTTP request count are saved in verification.json.","", "| Region | Scenario | Seed | Hours | Live tumor | Death commitments | Recruited CD8 | Hypoxic tumor | Decisions | Estimated API requests |", "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    lines += [f"| B{r['region']} | {r['scenario']} | {r['seed']} | {r['hours']:g} | {r['tumor']} | {r['kills']} | {r['recruited']} | {100*r['hypoxic_fraction']:.1f}% | {r['decisions']} | {r['calls_estimate']} |" for r in rows]
    lines += ["", "Checks: episode and final-state fingerprints; exact saved final positions; individual accounting; no quiet B/plasma queries; per-cell daily caps; negative controls; field residual/mass balance; final non-overlap audit; identical field domains and matched initial oxygen for nerve controls.","", "The request estimate derives from observed menus and payload sizes. Actual requests are recorded separately; cached replay makes no new requests. No cost is inferred from these counts.","", "Decision-concentration flags (>50% in one type) are reported in verification.json. Review them before continuing a paid pilot. Hypoxia is an outcome: declaring half the vessels non-perfused does not guarantee a hypoxic patch."]
    (args.directory/"RESULTS.md").write_text("\n".join(lines)+"\n",encoding="utf8")


if __name__ == "__main__": main()
