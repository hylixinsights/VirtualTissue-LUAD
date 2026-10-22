"""Optional one-cell-per-request TypeSafe adapter. No keys or paid tests in source."""
import json
import urllib.request

from .engine import validate_answer
from .io import fingerprint


class BudgetExhausted(RuntimeError):
    budget_exhausted = True


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class JevProvider:
    name = "jev"

    def __init__(self, key, model, max_requests, transport=None):
        if not key or not model or "latest" in model or type(max_requests) is not int or max_requests < 1:
            raise ValueError("A key, pinned model and positive request budget are required")
        self.key, self.model, self.limit = key, model, max_requests
        self.transport = transport or self._remote
        self.requests = 0
        self.audit = []
        self.resolved_model = None

    def _remote(self, payload):
        request = urllib.request.Request("https://api.typesafe.ai/v1/systemone", data=json.dumps(payload).encode(), method="POST",
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + self.key})
        try:
            with urllib.request.build_opener(NoRedirect()).open(request, timeout=20) as response:
                raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ValueError("Response too large")
            return json.loads(raw)
        except Exception:
            # Do not expose request headers, credentials, or arbitrary provider text.
            raise RuntimeError("Jev transport failed; usage may be unknown; no automatic retry") from None

    def choose(self, requests):
        if self.requests + len(requests) > self.limit:
            raise BudgetExhausted("Budget cannot cover this complete decision round")
        answers = {}
        for request in requests:
            payload = dict(model=self.model, state=request["observation"], questions={"behavior": dict(type="choice",
                instructions="Choose one prevalidated local behavior. Do not infer identity, rates or death. No desired tissue outcome is supplied.",
                criteria={k: v["description"] + (f" Target cell {v['target_id']}." if v["target_id"] is not None else "") for k, v in request["options"].items()})})
            record = dict(cell_id=request["cell_id"], model_requested=self.model, request=payload, request_hash=fingerprint(payload), status="started", usage="unknown")
            self.requests += 1
            self.audit.append(record)
            try:
                response = self.transport(payload)
                record["response"] = response
                record["usage"] = response.get("usage", "unknown")
                returned = response.get("model")
                if not isinstance(returned, str) or not returned or self.resolved_model and returned != self.resolved_model:
                    raise ValueError("Missing or changed returned model identity")
                if set(response.get("answers", {})) != {"behavior"}:
                    raise ValueError("Invalid question keys")
                answer = response["answers"]["behavior"]
                if answer.get("type") != "choice":
                    raise ValueError("Unexpected primitive")
                validate_answer(answer, request["options"])
                self.resolved_model = returned
                answers[request["cell_id"]] = answer
                record["status"] = "validated"
            except Exception:
                record["status"] = "failed; round proposals withheld"
                raise RuntimeError("Jev response failed validation or transport; round proposals withheld") from None
        return answers
