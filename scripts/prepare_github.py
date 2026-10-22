"""Prepare an allowlisted LUAD repository and selected replay for later user upload."""
import argparse,json,re,shutil,sys,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from luad_tissue.io import file_hash,write_json
from package_release import release_files
from verify_site import verify


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--site',type=Path,required=True)
    p.add_argument('--output',type=Path,default=ROOT/'outputs/github-upload/VirtualTissue-LUAD')
    p.add_argument('--archive',type=Path,default=ROOT/'dist/VirtualTissue-LUAD-ready-to-upload.zip')
    args=p.parse_args();review=verify(args.site)
    source={p.relative_to(ROOT).as_posix():p for p in release_files()}
    site_manifest=json.loads((args.site/'site-manifest.json').read_text(encoding='utf8'))
    source.update({'site/'+name:args.site/name for name in set(site_manifest['files'])|{'site-manifest.json'}})
    if args.output.exists():
        extras={p.relative_to(args.output).as_posix() for p in args.output.rglob('*') if p.is_file()}-set(source)-{'UPLOAD.md','upload-manifest.json'}
        if extras:raise SystemExit('Upload directory contains unselected files; use a new directory')
    secret=re.compile(rb'apikey_[0-9a-f]{32}_[0-9a-f]{32,}')
    for name,path in source.items():
        raw=path.read_bytes()
        if secret.search(raw):raise SystemExit('Credential-like literal in selected file: '+name)
        dest=args.output/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
    instructions='''# Upload this prepared repository

Destination: https://github.com/hylixinsights/VirtualTissue-LUAD.git

This folder is prepared locally. No files were pushed and no website was deployed.
It contains allowlisted source and one selected, recorded tissue example in `site/`.
The example includes per-cell Xenium-derived geometry, annotations and local states.
It is not an anonymized dataset. Raw H5AD inputs, other runs, request journals,
credentials, environments and caches are absent.

1. Review `site/model.html`, `site/provenance.json` and `upload-manifest.json`.
2. Commit this folder to the intended repository using your preferred Git client.
3. To host the replay, select GitHub Actions as the Pages source in the repository.
4. Manually run **Publish selected LUAD replay**. The workflow verifies the site
   before deployment. It does not invoke Python simulation or Jev on GitHub.

The expected Pages path is https://hylixinsights.github.io/VirtualTissue-LUAD/.
It becomes available only after your deployment succeeds. You can also host the
contents of `site/` under another subdirectory; links are relative.

The full inspectable trajectory is `site/recordings/episode.luad2.json.gz`.
The embedded player and the downloadable recording are verified to agree.
A request cap is a ceiling; completed simulations may use fewer requests.
'''
    (args.output/'UPLOAD.md').write_text(instructions,encoding='utf8')
    names=sorted(set(source)|{'UPLOAD.md'})
    manifest=dict(destination='https://github.com/hylixinsights/VirtualTissue-LUAD.git',published=False,
        selected_recording=review,files={name:file_hash(args.output/name) for name in names},
        includes_selected_per_cell_data=True,
        excluded=['raw inputs','unselected recordings','request journals','credentials','environments','caches','Git history'])
    write_json(args.output/'upload-manifest.json',manifest)
    args.archive.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(args.archive,'w',zipfile.ZIP_DEFLATED) as z:
        for name in names+['upload-manifest.json']:z.write(args.output/name,name)
    with zipfile.ZipFile(args.archive) as z:
        assert z.testzip() is None and set(z.namelist())==set(names)|{'upload-manifest.json'}
        for name,digest in manifest['files'].items():
            import hashlib
            assert hashlib.sha256(z.read(name)).hexdigest()==digest
    print(json.dumps(dict(folder=str(args.output),archive=str(args.archive),files=len(names)+1,
        provider=review['provider'],hours=review['hours'],calls=review['paid_calls'],published=False),indent=2))


if __name__=='__main__':main()
