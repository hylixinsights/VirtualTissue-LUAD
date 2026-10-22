"""M1 check: moving-geometry runs on a measured atlas with the declared local policy only.

No inference and no API key. Writes a private episode per scenario and an M1
report with t=0 fidelity, invariants, overlap audits, readouts and runtime.

    python scripts/run_v2_mechanics.py --atlas outputs/atlas_B26.json.gz --hours 72
"""
import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from luad_tissue.io import read_json, write_json  # noqa: E402
from luad_tissue.v2.runtime import SimulationV2  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--atlas", default=str(ROOT / "outputs/atlas_B26.json.gz"))
    parser.add_argument("--contract", default=str(ROOT / "contracts/runtime-v2.json"))
    parser.add_argument("--hours", type=float, default=72)
    parser.add_argument("--seed", type=int, default=21)
    parser.add_argument("--scenarios", default="static,m1_exercise")
    parser.add_argument("--migration-mode", choices=["self_propelled", "swap"], default=None,
                        help="override the contract default (records the override in the episode contract)")
    parser.add_argument("--out", default=str(ROOT / "outputs/v2"))
    args = parser.parse_args()
    atlas = read_json(args.atlas)
    contract = read_json(args.contract)
    if args.migration_mode:
        contract["migration"]["mode"] = args.migration_mode
    out = Path(args.out)
    report_path = out / f"m1_report_{atlas['patch_id']}_seed{args.seed}_{args.hours:g}h.json"
    report = dict(format="luad-v2-m1-report", contract_version=contract["version"], atlas=atlas["patch_id"],
                  atlas_fingerprint=atlas["fingerprint"], seed=args.seed, hours=args.hours, paid_calls=0, runs=[])
    if report_path.exists():
        # Separate invocations (one scenario each) merge into one report of the same setup.
        previous = read_json(report_path)
        if all(previous.get(k) == report[k] for k in ("contract_version", "atlas_fingerprint", "seed", "hours")):
            report = previous
    for scenario in args.scenarios.split(","):
        start = time.perf_counter()
        sim = SimulationV2(atlas, contract, scenario, args.seed)
        setup = time.perf_counter() - start
        audit0 = sim.tissue.overlap_audit()
        sim.run(int(round(args.hours * 60)))
        elapsed = time.perf_counter() - start
        audit_end = sim.tissue.overlap_audit()
        episode = sim.episode()
        name = f"{atlas['patch_id']}-{scenario}-{contract['migration']['mode']}-seed{args.seed}.luad2.json.gz"
        write_json(out / name, episode)
        summary = episode["summary"]
        run = dict(scenario=scenario, migration_mode=contract["migration"]["mode"], seconds_total=round(elapsed, 1),
                   seconds_setup=round(setup, 2), episode=name, episode_fingerprint=episode["fingerprint"],
                   overlap_audit=dict(t0=audit0, end=audit_end), summary=summary)
        report["runs"] = [r for r in report["runs"] if (r["scenario"], r["migration_mode"]) != (scenario, run["migration_mode"])] + [run]
        final = summary["final"]
        print(f"{scenario:12s} {contract['migration']['mode']:15s} {elapsed:6.1f}s  tumour {final['tumour_cells']} "
              f"born {summary['accounting']['born']} blocked {summary['events'].get('division_blocked_crowding', 0)} "
              f"cd8-tumour {final['cd8_tumour_contacts']} P_mean {final['pressure_mean']} hidden {final['hidden']} "
              f"overlap {audit_end['overlap_um2']}", flush=True)
    report["t0_fidelity"] = sim.fidelity
    write_json(report_path, report)


if __name__ == "__main__":
    main()
