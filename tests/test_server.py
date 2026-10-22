import gzip
import importlib.util
import json
import threading
import urllib.error
import urllib.request
from pathlib import Path
from http.server import ThreadingHTTPServer
import pytest
from luad_tissue.io import write_json

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("luad_server",ROOT/"server.py")
server=importlib.util.module_from_spec(spec);spec.loader.exec_module(server)


@pytest.fixture
def studio_server(tmp_path,atlas):
    write_json(tmp_path/"atlas_B26.json.gz",atlas)
    studio=server.Studio(tmp_path)
    httpd=ThreadingHTTPServer(("127.0.0.1",0),server.make_handler(studio))
    thread=threading.Thread(target=httpd.serve_forever,daemon=True);thread.start()
    yield f"http://127.0.0.1:{httpd.server_port}",studio
    httpd.shutdown();httpd.server_close();thread.join()


def request(base,path,body=None,headers=None):
    req=urllib.request.Request(base+path,data=json.dumps(body).encode() if body is not None else None,
         headers={"Content-Type":"application/json",**(headers or {})})
    with urllib.request.urlopen(req) as r:return r.read()


def test_full_local_api_export_and_replay(studio_server):
    base,studio=studio_server
    request(base,"/api/new",dict(region="26",scenario="cognate"))
    state=json.loads(request(base,"/api/step",dict(steps=2)))
    assert state["snapshot"]["time_min"]==20
    raw=request(base,"/api/export")
    episode=json.loads(gzip.decompress(raw))
    assert json.loads(request(base,"/api/replay",episode))["verified"]
    episode["events"][0]["kind"]="tampered"
    with pytest.raises(urllib.error.HTTPError) as error:request(base,"/api/replay",episode)
    assert error.value.code==400
    assert list((studio.output/"runs").glob("*.gz"))


def test_filesystem_not_served(studio_server):
    base,_=studio_server
    for path in ["/.env","/rulebook/rulebook.json","/../README.md","/outputs/atlas_B26.json.gz"]:
        with pytest.raises(urllib.error.HTTPError) as error:request(base,path)
        assert error.value.code==404


def test_foreign_origin_and_host_rejected(studio_server):
    base,_=studio_server
    with pytest.raises(urllib.error.HTTPError) as error:request(base,"/api/new",{},headers={"Origin":"https://unrelated.example"})
    assert error.value.code==403
    with pytest.raises(urllib.error.HTTPError) as error:request(base,"/api/config",headers={"Host":"unrelated.example"})
    assert error.value.code==403
