"""Prepare one explicitly selected recording for static hosting; never publish it."""
import argparse,base64,hashlib,html,json,re,sys,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from luad_tissue.io import canonical,file_hash,read_json,write_json
from luad_tissue.v2.episode import portable_player,validate_episode

REPOSITORY='https://github.com/hylixinsights/VirtualTissue-LUAD'
SITE_FILES={'index.html','model.html','provenance.json','recordings/episode.luad2.json.gz','.nojekyll'}
SECRET=re.compile(rb'apikey_[0-9a-f]{32}_[0-9a-f]{32,}')


def build(recording,atlas_path,destination,allow_local=False):
    recording,atlas_path,destination=map(Path,(recording,atlas_path,destination))
    episode,atlas=read_json(recording),read_json(atlas_path)
    validate_episode(episode,atlas)
    if episode['summary']['stop_reason'] not in ('horizon_reached','request_cap_before_round'):
        raise ValueError('Select a completed or budget-stopped recording, not a running or failed checkpoint')
    if episode['provider']!='jev_batched_v2' and not allow_local:
        raise ValueError('A local preview needs --allow-local; it must never be labeled as Jev')
    if SECRET.search(canonical(episode)) or SECRET.search(canonical(atlas)):
        raise ValueError('Credential-like literal detected in selected data')
    if destination.exists():
        extras={p.relative_to(destination).as_posix() for p in destination.rglob('*') if p.is_file()}-SITE_FILES-{'site-manifest.json'}
        if extras:raise ValueError('Destination contains unselected files; choose a clean directory')
    destination.mkdir(parents=True,exist_ok=True)
    (destination/'recordings').mkdir(exist_ok=True)
    portable_player(episode,atlas,ROOT/'web',destination/'index.html')
    page=(destination/'index.html').read_text(encoding='utf8')
    page=page.replace('class="brand" href="/"','class="brand" href="./"')
    page=page.replace('<a href="/atlas" id="atlas-link">Measured atlas &amp; contact laboratory ↗</a>',
        '<a href="./model.html">Model &amp; provenance ↗</a><span id="atlas-link" hidden></span>')
    page=page.replace('<p id="assumptions"','<p class="note"><a href="./recordings/episode.luad2.json.gz" download>Download the recorded episode</a> · Static replay · No inference calls</p><p id="assumptions"')
    page=page.replace('<details class="new-run"','<details hidden class="new-run"')
    extra='.new-run{display:none!important}#load,.file,.controls>label{display:none!important}.controls .badge{margin-left:0}'
    page=page.replace('</style>',extra+'</style>')
    scripts=re.findall(r'<script>(.*?)</script>',page,re.S)
    styles=re.findall(r'<style>(.*?)</style>',page,re.S)
    def hashes(values):
        return ' '.join("'sha256-"+base64.b64encode(hashlib.sha256(v.encode()).digest()).decode()+"'" for v in values)
    policy=f"default-src 'none'; script-src {hashes(scripts)}; style-src {hashes(styles)}; img-src data: blob:; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'"
    page=page.replace('<head>','<head><meta http-equiv="Content-Security-Policy" content="'+policy+'">')
    assert '<script src=' not in page and '<link rel="stylesheet"' not in page
    (destination/'index.html').write_text(page,encoding='utf8')
    (destination/'recordings/episode.luad2.json.gz').write_bytes(recording.read_bytes())
    summary=episode['summary']
    metadata=dict(format='luad-static-provenance-v1',repository=REPOSITORY,provider=episode['provider'],
        patch=episode['patch_id'],scenario=episode['scenario'],seed=episode['seed'],
        modeled_hours=summary['time_min']/60,stop_reason=summary['stop_reason'],
        recorded_api_calls=episode['paid_calls'],individual_decisions=summary['decisions'],
        episode_sha256=file_hash(recording),episode_fingerprint=episode['fingerprint'],
        engine_fingerprint=episode.get('engine_fingerprint'),atlas_fingerprint=atlas['fingerprint'],
        contract=episode['contract']['version'],
        initial_roi_cells=atlas['summary']['n_roi'],final=summary['final'],
        scope='Recorded mechanistic experiment. Structural compression proxy from Xenium; kinetics and recognition remain assumptions. Not a patient prediction.',
        disclosure='Contains selected per-cell Xenium-derived geometry, annotations and recorded local states. This is not an anonymized or aggregate-only export.',
        replay='Embedded atlas and episode, checksum verified by the player. Network connections disabled by the static page Content Security Policy.',
        published=False)
    write_json(destination/'provenance.json',metadata)
    sections=[]
    for title,name in [('Recorded Jev campaign','docs/JEV_CAMPAIGN_5000.md'),('Implemented model','docs/AUTONOMOUS_RUNTIME.md'),('Compression calibration','docs/CALIBRATION.md'),('Lessons from VirtualTissue-LN','docs/LN_REVIEW.md')]:
        source=ROOT/name
        if source.exists():sections.append('<details><summary>'+html.escape(title)+'</summary><pre>'+html.escape(source.read_text(encoding='utf8'))+'</pre></details>')
    content=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LUAD · Model and provenance</title><style>body{{max-width:960px;margin:40px auto;padding:0 24px;background:#f2f3ed;color:#193f3a;font:16px/1.7 system-ui}}h1{{font-family:Georgia}}a{{color:#206e57}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.6 system-ui}}details{{margin:24px 0}}code{{overflow-wrap:anywhere}}</style></head><body><a href="./">← Replay tissue</a> · <a href="{REPOSITORY}">Source repository</a><h1>LUAD: one recorded tissue experiment</h1><p>{html.escape(episode['patch_id'])} · {html.escape(episode['provider'])} · {metadata['modeled_hours']:g} modeled hours · {metadata['recorded_api_calls']} recorded API calls.</p><p>Recording status: <strong>{html.escape(metadata['stop_reason'])}</strong>. Playback reads saved states and makes no inference calls. Event chapters select the first saved frame at or after a recorded event; they never create an intermediate biological state.</p><p>{html.escape(metadata['scope'])}</p><p>{html.escape(metadata['disclosure'])}</p><p><a href="./provenance.json">Machine-readable provenance</a> · <a href="./recordings/episode.luad2.json.gz" download>Full selected episode</a></p><p>Episode SHA-256: <code>{metadata['episode_sha256']}</code></p>{''.join(sections)}</body></html>'''
    (destination/'model.html').write_text(content,encoding='utf8')
    (destination/'.nojekyll').write_text('')
    manifest=dict(format='luad-static-site-v1',files={name:file_hash(destination/name) for name in sorted(SITE_FILES)},
        selected_recording_fingerprint=episode['fingerprint'],contains_per_cell_data=True,published=False)
    write_json(destination/'site-manifest.json',manifest)
    return metadata


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--recording',type=Path,required=True)
    p.add_argument('--atlas',type=Path,default=ROOT/'outputs/atlas_B26.json.gz')
    p.add_argument('--output',type=Path,default=ROOT/'outputs/publication/site')
    p.add_argument('--allow-local',action='store_true')
    p.add_argument('--zip',dest='archive',type=Path)
    args=p.parse_args()
    result=build(args.recording,args.atlas,args.output,args.allow_local)
    if args.archive:
        args.archive.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(args.archive,'w',zipfile.ZIP_DEFLATED) as z:
            for name in sorted(SITE_FILES|{'site-manifest.json'}):z.write(args.output/name,name)
    print(json.dumps({k:result[k] for k in ['provider','modeled_hours','stop_reason','recorded_api_calls','episode_sha256']},indent=2))
    print('Prepared locally. Selected per-cell data are included; no upload or publication occurred.')


if __name__=='__main__':main()
