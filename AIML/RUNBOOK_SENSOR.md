RailGuard Sensor Module — Runbook & Review Ledger

Detect → Decide → Repair (the SECONDS half) · v1.0 · 59 tests green
1. What exists (the map)
Piece	File	What it is
Synthetic world	ml_sensor/scenarios.py	constants (single source of truth), physics, rule ladder, seeded 4000-row generator + 4% noise
Training	ml_sensor/train.py	RF+XGB, 80/20 seeded split, winner → ml_sensor/model/decision_model.joblib
Live engine	ml_sensor/decide.py	R1 wall → model → R2 leash; pure Python, no fastapi/sqlmodel
Held-out eval	ml_sensor/eval_scenarios.py	10 hand scenarios; DRAFT now, owner JSON swap ready
The bridge	api/incident.py	POST /api/incident → decision + optional planner defect (INC-####)
Guards	tests/test_ml_sensor.py	8 tests incl. R1-spy, leakage wall, sqlmodel-select tripwire

Artifacts: ml_sensor/model/decision_model.joblib (3.4M),training_report.json, eval_report.json, data/scenarios.csv (display only).
2. Metrics (the honest numbers)

    Winner: XGBoost, macro F1 0.9012 on the 20% holdout (RF: 0.8867).Expected band [0.90, 0.96] — at the floor edge, which is honest: 4% labelnoise caps the ceiling near 0.96. A 0.99 here would be a leak, not a win.
    Per-class F1: caution 0.905 · reduce 0.942 · reroute 0.867 · e-stop 0.891.No starving class (all ≥ 11.2% support).
    Held-out eval: 10/10 (DRAFT stand-ins; target was 7+). Owner JSON pending.
    R2 fallback preview: 1.25% of test predictions under 0.55 confidence —tree ensembles are near-categorical here; the leash matters for tails, notthe median. Reported, never hidden.
    Live decision latency: ~13–18 ms (budget 100 ms). Includes validation,physics, model inference, reason assembly.
    R1 proven by spy test (model call count = 0 on catastrophic input).
    R2 proven by spy test (low confidence → rule-engine answer, source tagged).

3. The demo beats (curl-ready)

Beat 1 — DECIDE (the anchor): POST /api/incident with:  speed 120, dist 8.5, heavy_rain, alert true, sq 45, severity 9,  landslide_debris, no alternate, latency 1200, axle null, CLEAR,  schedule true, station 6.0, track_circuit→ emergency_stop, source=model, conf 0.9998, physics 8.46 vs 4.608, ~15ms.

Beat 1b — THE WALL (optional, strong for judges): same but speed 180,dist 3.0, snow, severity 9 → hard_rule, model never consulted.

Beat 2 — BRIDGE: Beat 1 + "create_repair_defect": true, "corridor": "ET-NGP"→ INC-0001, ENG, severity 5/5, safety_flag TRUE (Tier 1), 720 min.

Beat 3 — RE-PLAN: POST /api/solve → diff shows pinned SC-GTL APPROVED blockuntouched, minimal moves, new block for INC-0001. (Verify with /api/impact.)
4. Boot ritual (memorize this order)

cd ~/AIMLsource venv/bin/activate.fish        # venv dies with the terminalwhich python                          # MUST be ~/AIML/venv/bin/python                                      # (system 3.14 is GLIBC-broken)python -m planner.demo_state          # tests re-seed the DB by design;                                      # re-seed before ANY manual sessionuvicorn api.main:app --port 8000      # FOREGROUND, dedicated terminal

Port-squatter check (after ANY restart):

curl -s -X POST localhost:8000/api/incident -H "Content-Type: application/json" \  -d '{"train_speed_kmh":120,"distance_to_obstacle_km":8.5,"environmental_condition":"clear","signal_quality_percent":45,"severity_score":5,"obstruction_type":"space_laser","communication_latency_ms":500,"distance_from_station_km":6,"sensor_type":"track_circuit"}' \  -o /dev/null -w "%{http_code}\n"# 422 = new build. 404 = stale server. 000 = no server.

If port is held: pkill -f "uvicorn api.main:app" or lsof -ti :8000 | xargs kill.

Fresh clone with no joblib? The API self-heals: first request trainsin-process (seed 42, ~10s). No network needed at any point — dead WiFi safe.
5. Frontend contract (hand this to their team)

    Endpoint: POST /api/incident — full schema at http://localhost:8000/docs(Swagger is the ONLY contract truth — not this doc, not memory).
    Send the 14 raw fields ONLY. The schema has no braking-distance /safe-stopping / time-to-obstacle fields: computed values are display-only(locked decision 12). Sending them changes nothing.
    Response: action (4-vocab) + confidence + source (hard_rule / model /rule_fallback) + reasons[] + physics{} (render, never recompute) +probabilities{} + decision_latency_ms + within_100ms_budget.
    With create_repair_defect=true (+corridor): repair_defect{} with defect_id,INC-#### ref, department, severity, safety_flag, duration — this defectthen appears in /api/plan and /api/defects like any other.
    "dry" is accepted and normalized to "clear". Unknown anything → 422.
    incident-created defects are source_ref INC-#### (injects are INJ-####) —the timeline can badge them.

6. Defaults ledger (what I chose; silence = locked)

Confirmed by owner: axle_balance → value+missing (16 features) · weathermultipliers dict · rule ladder rungs 1–7 · stop_and_verify→emergency_stop ·dept mapping (ENG/TRD/SNT) · TRD for equipment_failure_ahead · ALWAYS createdefect when flag=true · self-heal boot · decision_latency_ms in response ·weather sampling 45/20/12/10/8/5 · gen latency 50–2000, API 10–5000 ·persist F1 winner only, report both.

Still open for sign-off (each one line to change):

    safety_flag = incident severity ≥ 8 — MY inference, now default. Theanchor lands Tier 1 because of it. Veto → change SAFETY_SEVERITY_THRESHOLD.
    Repair durations: BASE_HOURS × SEV_MULT (anchor: 8h × 1.5 = 720 min).Veto → one dict row.
    Eval JSON: paste your real 10 scenarios toml_sensor/eval_scenarios.json and re-run — the file prefers yours.
    Rung-1 trust-gate exemption (physics bypasses benign-type caps) —documented in rule_engine_action's docstring; still reversible.

7. Lessons paid for (the scar tissue)

    xgboost 2.x needs integer labels — the code↔action map lives in thebundle, serving never assumes ordering.
    sqlmodel's select, NOT sqlalchemy's, inside Session.exec — raw Rowsotherwise. Regression-tested now.
    Department enum members (ENG/TRD/SNT) are read from the enum at import,never hardcoded from memory.
    NaN/None flows through signatures as None — round(None) is a runtimesurprise; write signature functions against the feature contract's types.
    Stale uvicorn on :8000 answers health checks like it's current. Prove thebuild with a route only it has.
