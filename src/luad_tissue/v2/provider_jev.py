"""Bounded independent Choice batches with a durable, credential-free journal.

Write an intent before transport and a result before applying any answer. A
crash after intent is an unknown paid outcome; resume never sends it again.
Resume deterministically reruns the kernel from t=0 and reuses exact hashes.
"""
import json
import math
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from ..io import canonical, fingerprint
from ..providers import BudgetExhausted, NoRedirect


def payload(rows,model):
    return dict(model=model,state=dict(setting="Independent local cells in an uncalibrated LUAD SIM experiment.",
                semantics="Kernel owns clocks, geometry, damage, death and division. Probabilities are preferences, never rates. Use only the individual observation and offered options. RNA signatures are not protein competence."),
                questions={f"c{r['cell_id']}":dict(type="choice",instructions={"task":"Choose one permitted local behavior.","local_observation":r["observation"]},
                    criteria={k:v["description"] for k,v in r["options"].items()}) for r in rows})


def build_batches(requests,model,p):
    batches, batch = [],[]
    for r in requests:
        candidate = batch+[r]
        if len(candidate) > p["max_questions"] or len(canonical(payload(candidate,model))) > p["max_payload_bytes"]:
            if not batch: raise ValueError("Single question exceeds the request size limit")
            batches.append(batch)
            batch = [r]
            if len(canonical(payload(batch,model))) > p["max_payload_bytes"]:
                raise ValueError("Single question exceeds the request size limit")
        else: batch = candidate
    if batch: batches.append(batch)
    return batches


def normalize_answer(answer,options,p):
    if not isinstance(answer,dict) or answer.get("type") != "choice" or answer.get("choice") not in options:
        raise ValueError("Missing or illegal choice")
    probs = answer.get("probabilities")
    if not isinstance(probs,dict) or set(probs) != set(options):
        raise ValueError("Probability keys mismatch")
    if any(type(v) not in (int,float) or not math.isfinite(v) or not 0 <= v <= 1 for v in probs.values()):
        raise ValueError("Invalid probability")
    conf = answer.get("confidence")
    if type(conf) not in (int,float) or not math.isfinite(conf) or not 0 <= conf <= 1:
        raise ValueError("Invalid confidence")
    total = math.fsum(probs.values())
    if total <= 0 or abs(total-1) > p["rounding_tolerance_per_option"]*len(probs)+1e-9:
        raise ValueError("Probability sum outside rounding tolerance")
    best = max(probs,key=probs.get)
    choice = answer["choice"]
    gap = probs[best]-probs[choice]
    repairs = []
    if gap > p["argmax_repair_gap"]+1e-9: raise ValueError("Choice/argmax mismatch")
    if gap > 1e-9:
        choice = best
        repairs.append("small_argmax_gap")
    if abs(total-1) > 1e-9: repairs.append("rounded_sum_normalized")
    return dict(choice=choice,probabilities={k:v/total for k,v in probs.items()},confidence=conf,repairs=repairs)


class BatchedJevProvider:
    name = "jev_batched_v2"

    def __init__(self,key,model,max_requests,parameters,journal,transport=None,run_context=None):
        if not key or not model or "latest" in model or type(max_requests) is not int or max_requests < 1:
            raise ValueError("A process key, pinned model and positive cap are required")
        self.key,self.model,self.limit,self.p = key,model,max_requests,parameters
        self.transport = transport or self._remote
        self.journal = Path(journal)
        self.journal.parent.mkdir(parents=True,exist_ok=True)
        self.context = run_context or {}
        self.cache,self.audit = {},[]
        self.requests = 0
        self.resolved_model = None
        if self.journal.exists():
            lines = self.journal.read_text(encoding="utf8").splitlines()
            for line in lines:
                try: entry = json.loads(line)
                except ValueError: raise ValueError("Incomplete journal; preserve it for review, do not resend uncertain requests") from None
                if entry.get("context") != self.context: raise ValueError("Journal belongs to another simulation contract/seed/atlas")
                h = entry["hash"]
                if entry["phase"] == "intent":
                    if entry["request"]["model"] != self.model: raise ValueError("Journal model differs from requested model")
                    self.requests += 1
                    self.cache[h] = {"status":"unknown_after_intent"}
                else:
                    self.cache[h] = entry
                    returned = entry.get("response",{}).get("model")
                    if self.resolved_model is None and entry["status"] == "received" and isinstance(returned,str): self.resolved_model = returned
        if self.requests > self.limit: raise ValueError("Cap is below already journaled calls")

    def append(self,entry):
        entry = {**entry,"context":self.context}
        raw = canonical(entry).decode().replace(self.key,"[redacted]")
        with self.journal.open("a",encoding="utf8",newline="\n") as stream:
            stream.write(raw+"\n")
            stream.flush()
            os.fsync(stream.fileno())

    def _remote(self,body):
        req = urllib.request.Request("https://api.typesafe.ai/v1/systemone",data=canonical(body),method="POST",headers={"Authorization":"Bearer "+self.key,"Content-Type":"application/json"})
        try:
            with urllib.request.build_opener(NoRedirect()).open(req,timeout=30) as response:
                raw = response.read(self.p["max_response_bytes"]+1)
            if len(raw) > self.p["max_response_bytes"]: raise ValueError("Response exceeds limit")
            return json.loads(raw)
        except urllib.error.HTTPError as e:
            detail = e.read(4096).decode("utf8","replace").replace(self.key,"[redacted]")
            raise RuntimeError(f"HTTP {e.code}: {detail}") from None
        except Exception:
            raise RuntimeError("Transport failed; usage unknown; no retry") from None

    def choose(self,requests):
        batches = build_batches(requests,self.model,self.p)
        bodies = [payload(batch,self.model) for batch in batches]
        hashes = [fingerprint(body) for body in bodies]
        required = sum(h not in self.cache for h in hashes)
        if self.requests+required > self.limit: raise BudgetExhausted("Cap cannot cover the complete decision round")
        answers = {}
        for batch,body,h in zip(batches,bodies,hashes):
            cached = h in self.cache
            if cached:
                entry = self.cache[h]
            else:
                self.append(dict(phase="intent",hash=h,request=body,usage="unknown"))
                self.requests += 1
                self.cache[h] = {"status":"unknown_after_intent"}
                start = time.monotonic()
                try:
                    response = self.transport(body)
                    # Redact before the response can enter journals or episodes.
                    response = json.loads(canonical(response).decode().replace(self.key,"[redacted]"))
                    entry = dict(phase="result",hash=h,status="received",response=response,latency_s=round(time.monotonic()-start,3),usage=response.get("usage","unknown"))
                except Exception as e:
                    entry = dict(phase="result",hash=h,status="transport_failed",error=str(e).replace(self.key,"[redacted]")[:4096],usage="unknown")
                self.append(entry)
                self.cache[h] = entry
            audit = dict(request_hash=h,cached=cached,status=entry["status"],cells=[r["cell_id"] for r in batch],usage=entry.get("usage","unknown"),validation={})
            response = entry.get("response",{})
            returned = response.get("model") if isinstance(response,dict) else None
            valid_model = isinstance(returned,str) and bool(returned) and (self.resolved_model is None or self.resolved_model == returned)
            if not valid_model or entry["status"] != "received":
                audit["status"] = "batch_invalid_or_unknown"
                self.audit.append(audit)
                continue
            self.resolved_model = returned
            audit["model_returned"] = returned
            upstream = response.get("answers")
            upstream = upstream if isinstance(upstream,dict) else {}
            expected = {f"c{r['cell_id']}" for r in batch}
            audit["extra_question_keys"] = sorted(set(upstream)-expected)
            for r in batch:
                cid = r["cell_id"]
                raw = upstream.get(f"c{cid}")
                try:
                    normalized = normalize_answer(raw,r["options"],self.p)
                    answers[cid] = normalized
                    audit["validation"][str(cid)] = dict(status="valid",raw=raw,repairs=normalized["repairs"])
                except (ValueError,TypeError) as e:
                    audit["validation"][str(cid)] = dict(status="invalid",reason=str(e),raw=raw)
            self.audit.append(audit)
        return answers
