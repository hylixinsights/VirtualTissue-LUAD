"""Build a measured B26/B27 atlas without modifying source files."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from luad_tissue.atlas import build_atlas
from luad_tissue.io import write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT.parent)
    parser.add_argument("--candidate", type=int, default=26)
    parser.add_argument("--halo-um", type=float, default=30)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    atlas = build_atlas(ROOT, args.data_dir, args.candidate, halo_um=args.halo_um)
    output = args.output or ROOT / f"outputs/atlas_B{args.candidate}.json.gz"
    write_json(output, atlas)
    write_json(output.parent / f"audit_B{args.candidate}.json", {k: v for k, v in atlas.items() if k not in ("cells", "signatures")})
    print(f"Built {atlas['patch_id']}: {atlas['summary']}")
    print(f"Saved {output}")


if __name__ == "__main__":
    main()
