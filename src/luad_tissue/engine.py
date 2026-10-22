"""Fixed-geometry causal laboratory, never a fitted patient trajectory."""
import copy
import math
import random
from collections import Counter

from .conditions import cell_report
from .io import fingerprint


def validate_answer(answer, options):
    if not isinstance(answer, dict) or answer.get("choice") not in options:
        raise ValueError("Unknown or missing choice")
    probs = answer.get("probabilities")
    if not isinstance(probs, dict) or set(probs) != set(options):
        raise ValueError("Probability keys must exactly match submitted options")
    if any(type(v) not in (float, int) or not math.isfinite(v) or not 0 <= v <= 1 for v in probs.values()):
        raise ValueError("Invalid probability value")
    if abs(sum(probs.values()) - 1) > 1e-6:
        raise ValueError("Probabilities must sum to one")
    confidence = answer.get("confidence")
    if type(confidence) not in (int, float) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
        raise ValueError("Invalid confidence")
    if probs[answer["choice"]] + 1e-6 < max(probs.values()):
        raise ValueError("Choice is not a maximum-probability option")


class LocalPolicy:
    """Declared intervention-first preview; no learned biological probabilities."""
    name = "local_policy"

    def choose(self, requests):
        answers = {}
        for request in requests:
            choices = [k for k in request["options"] if k != "wait"]
            choice = choices[0] if choices else "wait"
            answers[request["cell_id"]] = dict(choice=choice, probabilities={k: float(k == choice) for k in request["options"]}, confidence=1)
        return answers


class Simulation:
    def __init__(self, atlas, rulebook, contract, scenario="baseline", seed=21, provider=None):
        if scenario not in contract["scenarios"]:
            raise ValueError("Unsupported scenario")
        self.atlas = atlas
        self.rules = rulebook["rules"]
        self.contract = copy.deepcopy(contract)
        self.p = contract["numerical_assumptions"]
        self.scenario_id = scenario
        self.scenario = copy.deepcopy(contract["scenarios"][scenario])
        self.seed, self.rng = seed, random.Random(seed)
        self.by_id = {c["cell_id"]: c for c in atlas["cells"]}
        self.state = {cid: dict(viability="alive", damage_au=0., pulses_remaining=self.p["effector_pulses"] if self.scenario["effector_competence"] and c["identity"]["candidates"][0]["label"] == "T_CD8_cytotoxic" else 0,
                               cooldown_until=0, next_decision=0, processed_targets=0, program=None, death_due=None)
                      for cid, c in self.by_id.items() if c["role"] == "roi"}
        self.time = 0
        self.events, self.decisions, self.failures = [], [], []
        self.frames = []
        self.provider = provider or LocalPolicy()
        self.stop_reason = None
        self.initial_pulses = sum(s["pulses_remaining"] for s in self.state.values())
        self.spent_pulses = 0
        self.frames.append(self.snapshot())

    def derived_state(self):
        return {cid: {**s, "cooldown_complete": self.time >= s["cooldown_until"],
                     "decision_due": self.time >= s["next_decision"],
                     "processing_capacity_available": s["processed_targets"] < self.p["clearance_capacity"] and s["program"] is None}
                for cid, s in self.state.items()}

    def report(self, cid):
        return cell_report(self.by_id[cid], self.by_id, self.rules, self.contract, self.derived_state(), self.scenario)

    def requests(self):
        requests = []
        derived = self.derived_state()
        for cid, state in self.state.items():
            if state["viability"] != "alive" or state["program"] is not None or self.time < state["next_decision"]:
                continue
            cell = self.by_id[cid]
            primary = cell["identity"]["candidates"][0]["label"]
            if primary not in ("T_CD8_cytotoxic", "Macrophage_SPP1"):
                continue
            reports = cell_report(cell, self.by_id, self.rules, self.contract, derived, self.scenario)
            options = {"wait": dict(description="Start no new program during this decision interval.", target_id=None)}
            for report in reports:
                if report["rule_id"] not in self.contract["handler_rules"]:
                    continue
                for target in report["targets"]:
                    if target["result"] != "true":
                        continue
                    tid = target["target_id"]
                    action = "degranulate" if report["rule_id"].startswith("CD8_") else "efferocytose"
                    options[f"{action}:{tid}"] = dict(description="Begin a timed contact program: " + action,
                        target_id=tid, action=action, rule_id=report["rule_id"])
            if len(options) == 1:
                continue
            nearby = []
            for edge in cell["contacts"]:
                target = self.by_id[edge["cell_id"]]
                nearby.append(dict(cell_id=target["cell_id"], role=target["role"], identity=target["identity"],
                    gap_um=edge["gap_um"], interface_um=edge["interface_um"],
                    viability=self.state.get(target["cell_id"], {}).get("viability", "unknown")))
            observation = dict(cell_id=cid, identity=cell["identity"], own_state=copy.deepcopy(state), contacts=nearby,
                recognition=self.scenario["recognition"], effector_competence=self.scenario["effector_competence"],
                checkpoint_declared=self.scenario["checkpoint"], blockade_declared=self.scenario["blockade"],
                evidence="Geometry and identity candidates are measured. Recognition, competence, damage and clocks are SIM assumptions.",
                probability_semantics="model preference, never a biological event rate",
                excluded_rules=[dict(rule_id=r["rule_id"], reasons=[c["path"] for c in r["checks"] if c["result"] != "true"]) for r in reports if r["result"] != "true"])
            requests.append(dict(cell_id=cid, observation=observation, options=options))
        return requests

    def event(self, kind, actor=None, target=None, **fields):
        self.events.append(dict(index=len(self.events), time_min=self.time, kind=kind, actor=actor, target=target, **fields))

    def step(self):
        if self.stop_reason:
            return self.snapshot()
        if self.time >= self.p["horizon_min"]:
            self.stop_reason = "horizon_reached"
            return self.snapshot()
        requests = self.requests()
        answers, failure = {}, None
        if requests:
            try:
                answers = self.provider.choose(copy.deepcopy(requests))
                if set(answers) != {r["cell_id"] for r in requests}:
                    raise ValueError("Missing or extra cell decisions")
                for request in requests:
                    validate_answer(answers[request["cell_id"]], request["options"])
            except Exception as exc:
                # Budget refusal occurs before a complete round; stop and retain
                # pending clocks for export rather than silently extending a run.
                if getattr(exc, "budget_exhausted", False):
                    self.stop_reason = "request_budget_exhausted"
                    return self.snapshot()
                failure = type(exc).__name__ + ": " + str(exc)
                self.failures.append(dict(time_min=self.time, reason=failure, behavior="no new programs; existing clocks continue"))
                answers = {}
        order = list(requests)
        self.rng.shuffle(order)
        reserved = set()
        for request in order:
            cid = request["cell_id"]
            own = self.state[cid]
            own["next_decision"] = self.time + self.p["decision_interval_min"]
            answer = answers.get(cid)
            receipt = "provider_failure" if answer is None else "wait"
            if answer is not None:
                option = request["options"][answer["choice"]]
                target = option["target_id"]
                if target is not None:
                    if cid in reserved or target in reserved:
                        receipt = "conflict_deferred"
                    else:
                        reserved.update((cid, target))
                        duration = self.p["contact_program_min"] if option["action"] == "degranulate" else self.p["clearance_min"]
                        own["program"] = dict(action=option["action"], target=target, start=self.time, due=self.time + duration)
                        receipt = "program_started"
                        self.event("program_started", cid, target, action=option["action"], due_min=self.time + duration)
            self.decisions.append(dict(time_min=self.time, provider=self.provider.name, cell_id=cid,
                request=request, state_hash=fingerprint(request["observation"]), answer=answer, receipt=receipt,
                scenario=self.scenario_id, contract_version=self.contract["version"]))
        self.time = min(self.time + self.p["tick_min"], self.p["horizon_min"])
        self.advance_programs()
        self.check_invariants()
        if self.time >= self.p["horizon_min"]:
            self.stop_reason = "horizon_reached"
        snapshot = self.snapshot()
        self.frames.append(snapshot)
        return snapshot

    def advance_programs(self):
        for cid in sorted(self.state):
            own = self.state[cid]
            if own["viability"] == "apoptosis_committed" and self.time >= own["death_due"]:
                own["viability"] = "dead_intact"
                self.event("death_completed", cid)
            program = own["program"]
            if not program or self.time < program["due"]:
                continue
            own["program"] = None
            tid = program["target"]
            target = self.state[tid]
            touching = any(e["cell_id"] == tid and e["gap_um"] <= 1 for e in self.by_id[cid]["contacts"])
            if own["viability"] != "alive" or not touching or target["viability"] == "cleared":
                self.event("program_cancelled", cid, tid, reason="actor, target or contact unavailable")
                continue
            if program["action"] == "degranulate":
                if target["viability"] != "alive" or own["pulses_remaining"] <= 0:
                    self.event("program_cancelled", cid, tid, reason="target not alive or effector store depleted")
                    continue
                own["pulses_remaining"] -= 1
                self.spent_pulses += 1
                own["cooldown_until"] = self.time + self.p["cooldown_min"]
                factor = self.p["checkpoint_damage_factor"] if self.scenario["checkpoint"] and not self.scenario["blockade"] else 1.
                amount = self.p["pulse_damage_au"] * factor
                target["damage_au"] += amount
                self.event("damage_delivered", cid, tid, damage_au=amount, checkpoint_factor=factor)
                if target["damage_au"] >= self.p["death_threshold_au"]:
                    target.update(viability="apoptosis_committed", death_due=self.time + self.p["death_commitment_min"], program=None)
                    self.event("apoptosis_committed", tid, cause="model damage threshold")
            elif program["action"] == "efferocytose":
                if target["viability"] not in ("apoptosis_committed", "dead_intact") or own["processed_targets"] >= self.p["clearance_capacity"]:
                    self.event("program_cancelled", cid, tid, reason="clearance prerequisite lost")
                    continue
                target.update(viability="cleared", program=None)
                own["processed_targets"] += 1
                self.event("target_cleared", cid, tid)

    def check_invariants(self):
        if len(self.state) != self.atlas["summary"]["n_roi"]:
            raise AssertionError("Individual-cell accounting changed")
        if sum(s["pulses_remaining"] for s in self.state.values()) + self.spent_pulses != self.initial_pulses:
            raise AssertionError("Effector material was created or lost")
        for state in self.state.values():
            if state["damage_au"] < 0 or state["pulses_remaining"] < 0 or state["processed_targets"] > self.p["clearance_capacity"]:
                raise AssertionError("Invalid resource accounting")
            if state["viability"] != "alive" and state["program"] is not None:
                raise AssertionError("A nonliving cell has an active program")
        cleared = [event["target"] for event in self.events if event["kind"] == "target_cleared"]
        if len(set(cleared)) != len(cleared):
            raise AssertionError("A target was cleared more than once")

    def snapshot(self):
        return dict(time_min=self.time, scenario=self.scenario_id, provider=self.provider.name,
            stop_reason=self.stop_reason, counts=dict(Counter(s["viability"] for s in self.state.values())),
            decision_count=len(self.decisions), event_count=len(self.events), failure_count=len(self.failures),
            spent_pulses=self.spent_pulses, cells=copy.deepcopy(self.state))

    def episode(self):
        data = dict(format="luad-episode-v1", patch_id=self.atlas["patch_id"], atlas_fingerprint=self.atlas["fingerprint"],
            contract=self.contract, seed=self.seed, scenario=self.scenario_id, provider=self.provider.name,
            provider_audit=copy.deepcopy(getattr(self.provider, "audit", [])),
            initial_pulses=self.initial_pulses, frames=self.frames, decisions=self.decisions, events=self.events,
            failures=self.failures, final=self.snapshot(), scope="Fixed geometry, uncalibrated scenario. No migration, growth or molecular time series.")
        return {**copy.deepcopy(data), "fingerprint": fingerprint(data)}
