"""Verify an exact static-site allowlist and the embedded private recording."""
import argparse,base64,gzip,hashlib,json,re
from pathlib import Path


def verify(folder):
    folder=Path(folder)
    manifest=json.loads((folder/'site-manifest.json').read_text(encoding='utf8'))
    expected=set(manifest['files'])|{'site-manifest.json'}
    allowed={'index.html','model.html','provenance.json','recordings/episode.luad2.json.gz','.nojekyll','site-manifest.json'}
    if expected!=allowed:raise ValueError('Unexpected site allowlist')
    actual={p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}
    if actual!=expected:raise ValueError('Unselected or missing site files')
    for name,digest in manifest['files'].items():
        if hashlib.sha256((folder/name).read_bytes()).hexdigest()!=digest:raise ValueError('Site file integrity mismatch: '+name)
    page=(folder/'index.html').read_text(encoding='utf8')
    if "connect-src 'none'" not in page or '<script src=' in page or '<link rel="stylesheet"' in page:
        raise ValueError('Static page network isolation missing')
    match=re.search(r'<script id="portable-data" type="application/octet-stream" data-sha256="([0-9a-f]+)">([^<]+)</script>',page)
    if not match:raise ValueError('Embedded recording missing')
    raw=base64.b64decode(match[2],validate=True)
    if hashlib.sha256(raw).hexdigest()!=match[1]:raise ValueError('Embedded payload integrity mismatch')
    bundle=json.loads(gzip.decompress(raw))
    external=json.loads(gzip.decompress((folder/'recordings/episode.luad2.json.gz').read_bytes()))
    if bundle['episode']!=external:raise ValueError('Download and embedded episode disagree')
    def fingerprint(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    if fingerprint({k:v for k,v in external.items() if k!='fingerprint'})!=external['fingerprint']:raise ValueError('Episode fingerprint mismatch')
    if fingerprint(external['final_state'])!=external['final_state_fingerprint']:raise ValueError('Final state fingerprint mismatch')
    if bundle['atlas']['fingerprint']!=external['atlas_fingerprint']:raise ValueError('Atlas identity mismatch')
    if re.search(rb'apikey_[0-9a-f]{32}_[0-9a-f]{32,}',raw+gzip.decompress(raw)):raise ValueError('Credential-like literal detected')
    for body in re.findall(r'<script>(.*?)</script>|<style>(.*?)</style>',page,re.S):
        value=body[0] or body[1]
        digest=base64.b64encode(hashlib.sha256(value.encode()).digest()).decode()
        if "'sha256-"+digest+"'" not in page:raise ValueError('Inline content security hash mismatch')
    return dict(verified=True,files=len(expected),provider=external['provider'],hours=external['summary']['time_min']/60,
        paid_calls=external['paid_calls'],fingerprint=external['fingerprint'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--site',type=Path,required=True)
    print(json.dumps(verify(p.parse_args().site),indent=2))
