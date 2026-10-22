import importlib.util
import json
from pathlib import Path
import pytest
from luad_tissue.io import write_json
from test_v2_fields_programs import sim

ROOT=Path(__file__).resolve().parents[1]


def module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py')
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


@pytest.fixture
def completed(sim,tmp_path):
    episode=sim.run(120).episode()
    write_json(tmp_path/'episode.json.gz',episode);write_json(tmp_path/'atlas.json.gz',sim.atlas)
    return tmp_path/'episode.json.gz',tmp_path/'atlas.json.gz',tmp_path/'site'


def test_static_site_is_self_contained_and_preserves_exact_recording(completed):
    episode,atlas,site=completed
    meta=module('build_site').build(episode,atlas,site,allow_local=True)
    result=module('verify_site').verify(site)
    assert result['verified'] and result['paid_calls']==0
    assert meta['provider']=='local_policy_v2' and meta['published'] is False
    assert (site/'recordings/episode.luad2.json.gz').read_bytes()==episode.read_bytes()
    html=(site/'index.html').read_text(encoding='utf8')
    assert 'connect-src \'none\'' in html and 'href="./model.html"' in html
    assert 'id="chapters"' in html and 'id="last-frame"' in html


def test_local_fixture_never_passes_as_default_jev_publication(completed):
    with pytest.raises(ValueError,match='allow-local'):module('build_site').build(*completed)


def test_site_refuses_unselected_files_and_detects_modified_download(completed):
    episode,atlas,site=completed;builder=module('build_site');verify=module('verify_site').verify
    builder.build(*completed,allow_local=True)
    (site/'unselected.json').write_text('{}')
    with pytest.raises(ValueError,match='unselected'):builder.build(*completed,allow_local=True)
    with pytest.raises(ValueError,match='Unselected'):verify(site)
    (site/'unselected.json').unlink()
    (site/'recordings/episode.luad2.json.gz').write_bytes(b'changed')
    with pytest.raises(ValueError,match='integrity'):verify(site)


def test_running_checkpoint_cannot_be_packaged_as_finished(sim,tmp_path):
    sim.step()
    write_json(tmp_path/'episode.json.gz',sim.episode());write_json(tmp_path/'atlas.json.gz',sim.atlas)
    with pytest.raises(ValueError,match='running or failed'):
        module('build_site').build(tmp_path/'episode.json.gz',tmp_path/'atlas.json.gz',tmp_path/'site',allow_local=True)


def test_manifest_cannot_expand_the_public_allowlist(completed):
    episode,atlas,site=completed;module('build_site').build(*completed,allow_local=True)
    path=site/'site-manifest.json';manifest=json.loads(path.read_text())
    manifest['files']['../unselected']='0'*64;path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError,match='allowlist'):module('verify_site').verify(site)
