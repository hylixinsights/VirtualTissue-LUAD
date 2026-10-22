"""Record a bounded fixed-geometry episode. Live inference is opt-in."""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from luad_tissue.engine import Simulation
from luad_tissue.io import read_json, write_json
from luad_tissue.providers import JevProvider


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--atlas", type=Path, default=ROOT / "outputs/atlas_B26.json.gz")
    parser.add_argument("--scenario", choices=["baseline", "recognition_off", "cognate", "checkpoint", "blockade"], default="baseline")
    parser.add_argument("--provider", choices=["local", "jev"], default="local")
    parser.add_argument("--model", default="jev-1.13.0")
    parser.add_argument("--max-requests", type=int)
    parser.add_argument("--seed", type=int, default=21)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    provider = None
    if args.provider == "jev":
        provider = JevProvider(os.environ.get("TYPESAFE_API_KEY"), args.model, args.max_requests)
    simulation = Simulation(read_json(args.atlas), read_json(ROOT / "rulebook/rulebook.json"), read_json(ROOT / "contracts/runtime-v1.json"), args.scenario, args.seed, provider)
    write_json(args.output, simulation.episode())
    while not simulation.stop_reason:
        simulation.step()
        write_json(args.output, simulation.episode())
    print({k: v for k, v in simulation.snapshot().items() if k != "cells"})


if __name__ == "__main__":
    main()
