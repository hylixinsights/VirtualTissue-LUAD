"""Export a private, self-contained offline HTML replay with its measured atlas."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from luad_tissue.io import read_json
from luad_tissue.v2.episode import portable_player


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("episode",type=Path)
    p.add_argument("--output",type=Path)
    args = p.parse_args()
    episode = read_json(args.episode)
    region = 27 if episode["patch_id"].endswith("B27") else 26
    atlas = read_json(ROOT/f"outputs/atlas_B{region}.json.gz")
    destination = args.output or args.episode.with_suffix("").with_suffix(".html")
    portable_player(episode,atlas,ROOT/"web",destination)
    print(f"Private offline player: {destination}. Contains per-cell measured data; excluded from public packaging.")


if __name__ == "__main__": main()
