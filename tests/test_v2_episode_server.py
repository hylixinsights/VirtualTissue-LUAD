import copy
import base64
import importlib.util
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from luad_tissue.io import fingerprint,write_json
from luad_tissue import __version__
from luad_tissue.providers import BudgetExhausted
from luad_tissue.v2.episode import portable_player,validate_episode
from test_v2_fields_programs import sim

ROOT=Path(__file__).resolve().parents[1]


def test_episode_fingerprints_final_state_and_frame_are_checked(sim):
    episode=sim.run(20).episode()
    assert validate_episode(episode,sim.atlas)["verified"]
    corrupted=copy.deepcopy(episode)
    corrupted["events"][0]["kind"]="corrupted"
    with pytest.raises(ValueError):validate_episode(corrupted,sim.atlas)
    corrupted=copy.deepcopy(episode)
    corrupted["frames"][-1]["x"][0]+=1
    corrupted["fingerprint"]=fingerprint({k:v for k,v in corrupted.items() if k!="fingerprint"})
    with pytest.raises(ValueError,match="positions"):validate_episode(corrupted,sim.atlas)


def test_portable_export_has_no_external_assets_and_embeds_private_payload(sim,tmp_path):
    path=tmp_path/"player.html"
    portable_player(sim.run(20).episode(),sim.atlas,ROOT/"web",path)
    html=path.read_text(encoding="utf8")
    assert 'id="portable-data"' in html and 'data-sha256=' in html
    assert '<script src=' not in html and '<link rel="stylesheet"' not in html
    assert "offline replay only" in html


def test_provider_budget_stops_before_physical_step(sim):
    class Capped:
        name="capped_fixture"
        audit=[]
        requests=0
        def choose(self,requests):raise BudgetExhausted()
    sim.policy=Capped()
    xy=sim.tissue.xy.copy()
    sim.step()
    assert sim.time==0 and (sim.tissue.xy==xy).all()
    assert sim.stop_reason=="request_cap_before_round"
    assert not sim.decisions and not sim.events


def test_new_v2_api_runs_saves_validates_and_rejects_path_traversal(sim,tmp_path):
    spec=importlib.util.spec_from_file_location("v2_test_server",ROOT/"server.py")
    server=importlib.util.module_from_spec(spec);spec.loader.exec_module(server)
    write_json(tmp_path/"atlas_B26.json.gz",sim.atlas)
    studio=server.Studio(tmp_path)
    httpd=ThreadingHTTPServer(("127.0.0.1",0),server.make_handler(studio))
    thread=threading.Thread(target=httpd.serve_forever,daemon=True);thread.start()
    base=f"http://127.0.0.1:{httpd.server_port}"
    def req(path,body=None):
        request=urllib.request.Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(request,timeout=20) as r:return r.read()
    try:
        assert b"A living model" in req("/")
        assert json.loads(req("/api/v2/config"))["version"]==__version__
        first=json.loads(req("/api/v2/new",dict(region="26",scenario="S1",seed=4)))
        assert first["summary"]["time_min"]==0
        last=json.loads(req("/api/v2/step",dict(steps=1)))
        assert last["summary"]["time_min"]==10
        assert json.loads(req("/api/v2/replay",last))["verified"]
        recordings=json.loads(req("/api/v2/recordings"))
        assert len(recordings)==1
        with pytest.raises(urllib.error.HTTPError):req("/api/v2/recording?name=../../.env")
        with pytest.raises(urllib.error.HTTPError):req("/api/v2/new",dict(seed=-1))
        with pytest.raises(urllib.error.HTTPError):req("/api/v2/save-view",dict(png="data:text/html;base64,PHNjcmlwdD4="))
        png=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j6t8AAAAASUVORK5CYII=")
        saved=json.loads(req("/api/v2/save-view",dict(png="data:image/png;base64,"+base64.b64encode(png).decode())))
        assert req(saved["url"])==png
        assert (tmp_path/"views"/saved["name"]).read_bytes()==png
    finally:
        httpd.shutdown();httpd.server_close();thread.join()
