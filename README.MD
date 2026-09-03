
```markdown
# 🚆 RailGuard AI: Dual-Brain Railway Maintenance & Decision System

> An intelligent, safety-critical railway operations platform combining **real-time sensor intelligence (Brain 1)** with **constraint-driven block scheduling (Brain 2)**.

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Frontend-Next.js%2014-black?style=flat&logo=next.js)](https://nextjs.org/)
[![XGBoost](https://img.shields.io/badge/ML%20Engine-XGBoost%20(91.26%25%20F1)-EB690A?style=flat)](https://xgboost.readthedocs.io/)
[![OR-Tools](https://img.shields.io/badge/Optimization-Google%20OR--Tools-4285F4?style=flat)](https://developers.google.com/optimization)
[![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?style=flat&logo=sqlite)](https://www.sqlite.org/)

---

## 📌 Overview

Modern rail operations require both sub-second safety responses on active tracks and optimal long-term maintenance resource allocation. **RailGuard AI** bridges these domains:

1. **Active Telemetry Ingestion:** Evaluates track, schedule, and axle sensors in real time.
2. **Safety-Critical Interventions:** Enforces physics-based braking limits and deterministic overrides before ML inference.
3. **Automated Planner Ingestion:** Dispatches high-severity hazards directly to the maintenance ledger as actionable work orders.
4. **Operations Optimization:** Employs constraint programming to pack track possessions and maintenance blocks without snarling commuter schedules.

---

## 🏗️ System Architecture

```text
 ┌────────────────────────────────────────────────────────┐
 │            16 Real-Time Telemetry Feeds                │
 │  (Speed, Obstacles, Weather, Axle Balance, Latency)   │
 └───────────────────────────┬────────────────────────────┘
                             │
                             ▼
 ┌────────────────────────────────────────────────────────┐
 │            BRAIN 1: Sensor Decision Engine             │
 │  backend/app/core/decision_engine.py                   │
 │                                                        │
 │   [Physics Engine]  ──► Braking Distance Verification  │
 │   [Safety Guard]    ──► Severity >= 9 Override (E-Stop)│
 │   [Inference]       ──► XGBoost Classifier             │
 │   [Fallback]        ──► Deterministic Rule Layer       │
 └───────────────────────────┬────────────────────────────┘
                             │
                  POST /api/v1/incident
             (Severity Map & Defect Creation)
                             │
                             ▼
 ┌────────────────────────────────────────────────────────┐
 │             BRAIN 2: Block & Track Planner             │
 │  backend/app/core/                                     │
 │                                                        │
 │   [Defect CRUD]     ──► Prioritization Engine (Score)  │
 │   [Solver]          ──► Google OR-Tools (CP-SAT)       │
 │   [Fallback]        ──► Greedy Interval Scheduler      │
 └───────────────────────────┬────────────────────────────┘
                             │
                             ▼
 ┌────────────────────────────────────────────────────────┐
 │           UI Dashboard & Visualization Layer           │
 │  Next.js 14 • Tailwind CSS • Recharts                  │
 └────────────────────────────────────────────────────────┘

```

---

## 🧠 The Dual-Engine Core

### Brain 1: Sensor-Decision Module

* **Path:** `backend/app/core/decision_engine.py`
* **Telemetry (16 Channels):** Train speed, obstacle distance, weather, severity score, obstruction type, network latency, sensor health, signal quality, block section status, axle load balance, train timetable delta, and nearest station distance.
* **Physics & Boundary Layer:**
* Computes dynamic stopping distance:

$$\text{Braking Distance} = \left(\frac{\text{Speed}}{100}\right)^2 \times 2.0 \times \text{Friction}$$


* Deterministic safety ceiling: Any severity $\ge 9$ triggers an instantaneous Emergency Stop override.


* **Model Layer:** XGBoost inference pipeline achieving a **91.26% F1 score** across edge-case benchmarks, supported by rule-based fallbacks during data dropouts.

### The Bridge: Sensor to Maintenance Pipeline

* **Path:** `backend/app/api/routes.py` (`POST /api/v1/incident`)
* Translates operational anomalies into track possessions:
* **Scale Normalization:** Maps sensor scale ($1\text{--}10$) to planner scale ($1\text{--}5$):

$$\text{Planner Severity} = \min(5,\, 1 + \lfloor\text{Severity} / 2\rfloor)$$


* **Critical Flagging:** Automatically assigns a baseline priority score of `100.0` for safety-critical hazards.
* **Audit Traceability:** Allocates an immutable defect reference (`INC-XXXXXX`) tagged with source origin `SENSOR_ML`.



### Brain 2: Block Planner & Optimizer

* **Path:** `backend/app/core/`
* **Defect Lifecycle Management:** Ingests anomalies, maintenance requests, and track possessions.
* **Rank & Score Engine:** Tiered multi-factor valuation based on network load, passenger throughput risk, and asset deterioration speed.
* **Dual-Mode Scheduling:**
* **Primary:** Google OR-Tools CP-SAT formulation satisfying track possession intervals, crew availability, and conflict-free windows.
* **Secondary:** Deterministic greedy scheduler for sub-millisecond dispatch if solvers timeout.



---

## 📡 API Reference

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/api/v1/incident` | Evaluates sensor payload and creates maintenance defect if flagged |
| `GET` | `/api/v1/defects` | Fetches all open track defects and status metadata |
| `POST` | `/api/v1/defects/score-all` | Re-runs the multi-factor scoring engine across open defects |
| `POST` | `/api/v1/solve` | Executes OR-Tools CP-SAT to calculate optimal maintenance schedule |
| `GET` | `/api/v1/plan` | Returns scheduled possession blocks and timeline gantt data |
| `GET` | `/api/v1/impact` | Returns operational yield metrics (hours saved, schedule improvements) |

---

## 🔬 Machine Learning Pipeline

* **Location:** `AIML/ml_sensor/`

```text
AIML/ml_sensor/
├── generate_scenarios.py   # Generates 4,000 synthetic operational edge cases
├── train.py                # Cross-evaluates RandomForest vs. XGBoost
├── eval_handcrafted.py     # Deterministic evaluation across 10 critical scenarios
└── decision_model.joblib   # Serialized production XGBoost model artifact

```

---

## 🛠️ Tech Stack & Service Map

| Component | Technology | Target | Role |
| --- | --- | --- | --- |
| **API Server** | FastAPI, SQLModel | `http://localhost:8000` | Orchestration, routes, logic execution |
| **Frontend** | Next.js, Tailwind, Recharts | `http://localhost:3000` | Telemetry dashboards, schedule Gantt |
| **Database** | SQLite | `backend/app.db` | Persistence for blocks, corridors, defects |
| **ML Engine** | scikit-learn, XGBoost | `AIML/ml_sensor/` | Real-time sensor decision inference |
| **Solver** | Google OR-Tools (CP-SAT) | Embedded | Mathematical track window optimization |

---

## 🚀 Getting Started

### Prerequisites

* Python 3.10+
* Node.js 18+ and `npm`

### 1. Backend & ML Setup

```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the API service
python -m app.main

```

* API Server will start at: `http://localhost:8000`
* Interactive Documentation (Swagger UI): `http://localhost:8000/docs`

### 2. Frontend Dashboard Setup

```bash
# Open a new terminal session
cd frontend

# Install Node modules
npm install

# Start development server
npm run dev

```

* Dashboard will be live at: `http://localhost:3000`

```

<FollowUp label="Want an incident payload example or Docker Compose setup?" query="Show me a sample JSON incident request body and a docker-compose.yml file to run this entire system."/>

```