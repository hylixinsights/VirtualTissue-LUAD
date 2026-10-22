"""Build a code/documentation export from an explicit allowlist, never the working tree."""
import sys
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from luad_tissue.io import file_hash,write_json

FILES=["README.md","MANUAL.md","AGENTS.md","NOTICE.md","pyproject.toml","requirements.lock",".gitignore","server.py","Start Studio.cmd"]
TREES={"src":{ ".py"},"web":{ ".html",".css",".js"},"tests":{ ".py"},"scripts":{ ".py"},"docs":{ ".md"},"contracts":{ ".json"},".github/workflows":{ ".yml"}}


def release_files():
    files=[ROOT/p for p in FILES]
    for directory,suffixes in TREES.items():
        files.extend(p for p in (ROOT/directory).rglob("*") if p.is_file() and p.suffix in suffixes and "__pycache__" not in p.parts)
    files.extend((ROOT/"rulebook").glob("*.schema.json"))
    files.extend(ROOT/"rulebook"/name for name in ("rulebook.json","question_templates.json"))
    # Aggregated calibration is needed to rebuild the atlas, and contains no cell
    # records. It remains explicitly documented as a derived LUAD3 artifact.
    files.append(ROOT/"rulebook/calibration.json")
    return sorted(set(files))


def main():
    files=release_files()
    manifest={str(p.relative_to(ROOT)).replace("\\","/"):file_hash(p) for p in files}
    destination=ROOT/"dist/luad-virtual-tissue-0.2.1.zip"
    destination.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(destination,"w",zipfile.ZIP_DEFLATED) as archive:
        for p in files:archive.write(p,str(p.relative_to(ROOT)))
    write_json(ROOT/"dist/release-manifest.json",dict(version="0.2.1",files=manifest,
        excluded="Raw inputs, per-cell patch examples, reconstructed atlases, private episodes, environments, keys, caches and Git history",
        license="No project-wide license assigned. See NOTICE.md."))
    print(f"Exported {len(files)} allowlisted files to {destination}")


if __name__=="__main__":main()
