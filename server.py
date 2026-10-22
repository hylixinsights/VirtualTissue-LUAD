"""Loopback-only atlas studio. The browser never receives an API key."""
import argparse
import base64
import gzip
import json
import mimetypes
import sys
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from luad_tissue.conditions import cell_report
from luad_tissue.engine import Simulation
from luad_tissue.io import canonical, fingerprint, read_json, write_json
from luad_tissue.v2.autonomous import AutonomousSimulation
from luad_tissue.v2.episode import validate_episode


class Studio:
    def __init__(self, output):
        self.output = Path(output)
        self.rb = read_json(ROOT / "rulebook/rulebook.json")
        self.contract = read_json(ROOT / "contracts/runtime-v1.json")
        self.atlases = {str(c): read_json(self.output / f"atlas_B{c}.json.gz") for c in (26, 27) if (self.output / f"atlas_B{c}.json.gz").exists()}
        if not self.atlases:
            raise ValueError("No atlas found. Run scripts/build_atlas.py first.")
        self.simulation = None
        self.run_id = None
        self.v2 = None
        self.v2_id = None
        self.contract2 = read_json(ROOT / "contracts/runtime-v2-calibrated.json")
        self.lock = threading.RLock()

    def recordings(self):
        return {("calibrated-"+p.name if directory=="calibrated-release" else p.name):p
                for directory in ("autonomous","autonomous-release","calibrated-release")
                for p in (self.output/directory).glob("*.luad2.json.gz") if p.is_file()}

    def save_v2(self):
        write_json(self.output/"autonomous"/f"{self.v2_id}.luad2.json.gz",self.v2.episode())

    def save(self):
        write_json(self.output / "runs" / f"{self.run_id}.luad.json.gz", self.simulation.episode())


def make_handler(studio):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def send_data(self, data, content_type="application/json", status=200, attachment=None):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' blob: data:; frame-ancestors 'none'")
            if attachment:
                self.send_header("Content-Disposition", f'attachment; filename="{attachment}"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def valid_host(self):
            return self.headers.get("Host") in (f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}")

        def do_GET(self):
            if not self.valid_host():
                return self.send_data(b'{"error":"Invalid local host"}', status=403)
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            try:
                with studio.lock:
                    region = query.get("region", ["26"])[0]
                    if parsed.path == "/api/config":
                        result = dict(regions=list(studio.atlases), contract=studio.contract, version="0.1.0")
                    elif parsed.path == "/api/v2/config":
                        result = dict(regions=list(studio.atlases),contract=studio.contract2,version="0.2.1",recordings=list(studio.recordings()))
                    elif parsed.path == "/api/v2/recordings":
                        result = list(studio.recordings())
                    elif parsed.path == "/api/v2/recording":
                        file = studio.recordings()[query["name"][0]]
                        return self.send_data(file.read_bytes(),"application/gzip",attachment=file.name)
                    elif parsed.path == "/api/v2/view":
                        name = query.get("name",[""])[0]
                        allowed = {p.name:p for p in (studio.output/"views").glob("view-*.png")}
                        return self.send_data(allowed[name].read_bytes(),"image/png",attachment=name)
                    elif parsed.path == "/api/v2/export" and studio.v2:
                        studio.save_v2()
                        return self.send_data(gzip.compress(canonical(studio.v2.episode()),mtime=0),"application/gzip",attachment=f"{studio.v2_id}.luad2.json.gz")
                    elif parsed.path == "/api/atlas":
                        result = studio.atlases[region]
                    elif parsed.path == "/api/cell":
                        cid = int(query["id"][0])
                        atlas = studio.atlases[region]
                        by_id = {c["cell_id"]: c for c in atlas["cells"]}
                        cell = by_id[cid]
                        is_run = studio.simulation and studio.simulation.atlas["patch_id"] == atlas["patch_id"] and query.get("live") == ["1"]
                        reports = studio.simulation.report(cid) if is_run and cell["role"] == "roi" else cell_report(cell, by_id, studio.rb["rules"], studio.contract) if cell["role"] == "roi" else []
                        decisions = [d for d in studio.simulation.decisions if d["cell_id"] == cid] if is_run else []
                        result = dict(cell=cell, reports=reports, decisions=decisions)
                    elif parsed.path == "/api/export" and studio.simulation:
                        return self.send_data(gzip.compress(canonical(studio.simulation.episode()), mtime=0), "application/gzip", attachment=f"{studio.run_id}.luad.json.gz")
                    elif parsed.path in ("/", "/index.html", "/atlas", "/app.js", "/style.css", "/autonomous.html", "/autonomous.js", "/autonomous.css"):
                        file = ROOT / "web" / ("autonomous.html" if parsed.path == "/" else "index.html" if parsed.path == "/atlas" else parsed.path[1:])
                        return self.send_data(file.read_bytes(), mimetypes.guess_type(file.name)[0] or "text/plain")
                    else:
                        return self.send_data(b'{"error":"Not found"}', status=404)
                    self.send_data(canonical(result))
            except (ValueError, KeyError) as error:
                self.send_data(canonical(dict(error=str(error))), status=400)

        def do_POST(self):
            if not self.valid_host() or self.headers.get("Origin") not in (f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}", None):
                return self.send_data(b'{"error":"Local origin required"}', status=403)
            if self.headers.get("Content-Type") != "application/json":
                return self.send_data(b'{"error":"JSON required"}', status=415)
            try:
                size = int(self.headers.get("Content-Length", "0"))
                limit = 8 * 1024 * 1024 if self.path == "/api/v2/save-view" else 256 * 1024 * 1024 if self.path == "/api/v2/replay" else 64 * 1024 * 1024 if self.path == "/api/replay" else 1024
                if not 0 < size <= limit:
                    raise ValueError("Invalid request size")
                body = json.loads(self.rfile.read(size))
                if not isinstance(body, dict):
                    raise ValueError("Request body must be an object")
                with studio.lock:
                    if self.path == "/api/v2/save-view":
                        encoded = body.get("png","")
                        if not isinstance(encoded,str) or not encoded.startswith("data:image/png;base64,"):
                            raise ValueError("PNG image required")
                        png = base64.b64decode(encoded.split(",",1)[1],validate=True)
                        if not png.startswith(b"\x89PNG\r\n\x1a\n") or len(png)>6*1024*1024:
                            raise ValueError("Invalid PNG or image too large")
                        folder = studio.output/"views"
                        folder.mkdir(exist_ok=True)
                        name = "view-"+uuid.uuid4().hex[:12]+".png"
                        (folder/name).write_bytes(png)
                        return self.send_data(canonical(dict(name=name,url="/api/v2/view?name="+name)))
                    elif self.path == "/api/v2/replay":
                        atlas = next((a for a in studio.atlases.values() if a["fingerprint"] == body.get("atlas_fingerprint")),None)
                        if atlas is None: raise ValueError("Matching measured atlas unavailable")
                        return self.send_data(canonical(validate_episode(body,atlas)))
                    elif self.path == "/api/v2/new":
                        seed = body.get("seed",21)
                        if type(seed) is not int or not 0 <= seed < 2**32: raise ValueError("Seed must be an unsigned 32-bit integer")
                        atlas = studio.atlases[str(body.get("region","26"))]
                        studio.v2 = AutonomousSimulation(atlas,studio.contract2,body.get("scenario","S1"),seed)
                        studio.v2_id = atlas["patch_id"]+"-interactive-"+uuid.uuid4().hex[:12]
                        studio.save_v2()
                        return self.send_data(canonical(studio.v2.episode()))
                    elif self.path == "/api/v2/step" and studio.v2:
                        steps = body.get("steps",6)
                        if type(steps) is not int or not 1 <= steps <= 6: raise ValueError("Step count must be 1–6")
                        for _ in range(steps): studio.v2.step()
                        studio.save_v2()
                        return self.send_data(canonical(studio.v2.episode()))
                    elif self.path == "/api/replay":
                        claimed = body.pop("fingerprint", None)
                        if body.get("format") != "luad-episode-v1" or claimed != fingerprint(body):
                            raise ValueError("Invalid recording format or fingerprint")
                        atlas = next((a for a in studio.atlases.values() if a["fingerprint"] == body.get("atlas_fingerprint")), None)
                        if atlas is None or not body.get("frames"):
                            raise ValueError("Recording atlas or frames unavailable")
                        return self.send_data(canonical(dict(verified=True)))
                    elif self.path == "/api/new":
                        atlas = studio.atlases[str(body.get("region", "26"))]
                        seed = body.get("seed", 21)
                        if type(seed) is not int or not 0 <= seed < 2**32:
                            raise ValueError("Seed must be an unsigned 32-bit integer")
                        studio.simulation = Simulation(atlas, studio.rb, studio.contract, body.get("scenario", "baseline"), seed)
                        studio.run_id = atlas["patch_id"] + "-" + uuid.uuid4().hex[:12]
                        studio.save()
                    elif self.path == "/api/step" and studio.simulation:
                        steps = body.get("steps", 1)
                        if type(steps) is not int or not 1 <= steps <= 6:
                            raise ValueError("Step count must be 1–6")
                        for _ in range(steps):
                            studio.simulation.step()
                            studio.save()
                    else:
                        raise ValueError("Create an experiment before stepping")
                    result = dict(snapshot=studio.simulation.snapshot(), events=studio.simulation.events[-20:], run_id=studio.run_id)
                self.send_data(canonical(result))
            except (ValueError, KeyError) as error:
                self.send_data(canonical(dict(error=str(error))), status=400)
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8026)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs")
    args = parser.parse_args()
    studio = Studio(args.output_dir)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(studio))
    print(f"LUAD Tissue Studio: http://127.0.0.1:{args.port} — local policy only; zero paid calls", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
