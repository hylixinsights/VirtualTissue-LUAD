"""Declared state-aware control policy; deterministic preferences, not inference."""


class LocalPolicyV2:
    name = "local_policy_v2"
    requests = 0
    audit = ()

    def choose(self, requests):
        out = {}
        for r in requests:
            obs = r["observation"]
            s, f = obs["sim_state"], obs["fields_sim"]
            priority = ["EFFEROCYTOSE", "HELP_CD8"]
            if obs.get("adrenergic_cycle_bias_sim"):
                priority += ["ENTER_CYCLE"]
            if s["exhaustion"] >= .4 or (obs["primary_label"] == "T_CD8_cytotoxic" and s["pulses"] == 0):
                priority += ["REST"]
            priority += ["DEGRANULATE", "PROLIFERATE", "SPROUT", "SECRETE_CXCL9"]
            if f["oxygen"] < .3:
                priority += ["GLYCOLYTIC_SHIFT", "SECRETE_VEGFA"]
            if f["ifng"] > .015 and s["pdl1"] < .5:
                priority += ["UPREGULATE_PDL1"]
            priority += ["ENTER_CYCLE", "MIGRATE_UP_CXCL9", "SCAN_RANDOM"]
            # Alternate available stromal secretion programs at independent checkpoints.
            rotation = int(obs["time_min"]//720) % 3
            stroma = ["DEPOSIT_MATRIX", "SECRETE_TGFB", "SECRETE_VEGFA"]
            priority += stroma[rotation:] + stroma[:rotation]
            priority += ["SECRETE_VEGFA_TGFB", "PATROL", "HOLD_POSITION", "REMAIN_QUIESCENT", "WAIT", "STAY_QUIESCENT"]
            keys = list(r["options"])
            choice = next((k for a in priority for k in keys if k.split(":")[0] == a), keys[0])
            out[r["cell_id"]] = dict(choice=choice, probabilities={k:float(k==choice) for k in keys}, confidence=1.)
        return out
