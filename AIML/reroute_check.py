"""
reroute_check.py -- is the model wrong, or is the ground truth not
what you expected?

For each scenario you test, prints:
  rule label (ground truth)  vs  model prediction
and buckets results:
  MODEL WRONG   : rule says reroute, model says something else
                  -> real model failures, retraining is the fix
  LADDER SAYS NO: rule itself says NOT reroute
                  -> the model is faithful; the question is whether
                     YOUR ladder should reroute here (owner decision)
  AGREE         : both say reroute

Usage:
    python reroute_check.py scenarios.json
where scenarios.json is a list of incident objects (the 14 fields).
"""

from __future__ import annotations

import json
import sys

from ml_sensor.decide import DecisionEngine
from ml_sensor.scenarios import rule_engine_action


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "scenarios.json"
    scenarios = json.loads(open(path).read())
    if isinstance(scenarios, dict):
        scenarios = scenarios.get("scenarios", [scenarios])

    engine = DecisionEngine()
    buckets = {"AGREE": 0, "MODEL_WRONG": 0, "LADDER_SAYS_NO": 0}

    print(f"{'#':<4}{'rule (truth)':<22}{'model':<22}{'verdict'}")
    print("-" * 70)
    for i, sc in enumerate(scenarios, 1):
        rule = rule_engine_action(sc)
        model = engine.decide(sc)["action"]
        if rule == "reroute" and model != "reroute":
            verdict = "MODEL_WRONG"
        elif rule != "reroute":
            verdict = "LADDER_SAYS_NO (model faithful)"
        else:
            verdict = "AGREE"
        buckets["LADDER_SAYS_NO" if verdict.startswith("LADDER") else verdict] += 1
        print(f"{i:<4}{rule:<22}{model:<22}{verdict}")

    n = len(scenarios)
    print("-" * 70)
    print(f"AGREE          : {buckets['AGREE']}/{n}")
    print(f"MODEL_WRONG    : {buckets['MODEL_WRONG']}/{n}  <- only these justify retraining")
    print(f"LADDER_SAYS_NO : {buckets['LADDER_SAYS_NO']}/{n}  <- ladder vs your intuition")
    print()
    print("If LADDER_SAYS_NO dominates: the model learned the ladder")
    print("correctly -- the question is whether the LADDER should say")
    print("reroute for these. That's an owner design decision, not a")
    print("training problem.")


if __name__ == "__main__":
    main()

