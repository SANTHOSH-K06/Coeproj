# Hospital Appointment Capacity Forecasting Engine (Review 1 — 35% Milestone)

A production-ready, multi-tenant healthcare appointment scheduling and database capacity forecasting system. Enforces database-level ACID double-booking prevention, tracks granular SQLite table and B-tree index storage, evaluates retention policies, and provides dual-model capacity forecasting (baseline linear vs. tenant-aware non-linear) with empirical backtesting.

---

## Key Features (Review 1 Milestone)
1. **Clinical Appointment Workflow**: Multi-tenant appointment booking across Hospital Alpha, Hospital Beta, and Hospital Gamma.
2. **ACID Double-Booking Prevention**: Database-level `UNIQUE(tenant_id, doctor_id, date, slot_time)` constraint preventing concurrent slot collisions with HTTP 409 Conflict.
3. **Role-Based Access Control (RBAC)**: Admin vs Staff roles with JWT authentication, PBKDF2 password hashing, and cross-tenant access denial (`HTTP 403 Forbidden`).
4. **Physical Storage Monitoring**: Direct measurement of SQLite data pages and secondary index pages for `appointments`, `patients`, `doctors`, and `appointment_slots`.
5. **Configurable Retention Rules**: 365-day active retention modeling comparing storage growth with vs without retention.
6. **Dual-Model Capacity Forecasting**:
   - **Baseline Model**: Linear extrapolation based on daily growth rate.
   - **Proposed Model**: Non-linear tenant-weighted model factoring index B-tree overhead, retention damping, confidence score (%), and 95% prediction intervals.
7. **Empirical Backtesting Experiments**: 3 simulated scenarios (Scenario A: Stable growth, Scenario B: Rapid tenant growth, Scenario C: Sudden activity spike) calculating exact forecast error ($\text{ABS}(\text{Predicted} - \text{Actual})$) with 78.3% error reduction.
8. **Interactive Dashboard**: Glassmorphism dark-mode UI with live charts, failure case simulators, and a guided 5–10 minute Review 1 demo mode.

---

## Quick Start

### 1. Launch Everything (One Command)
```bash
./start.sh
```
- **Web Dashboard**: `http://localhost:5173`
- **FastAPI API Docs**: `http://localhost:8000/docs`

### 2. Manual Startup
```bash
# Seed synthetic data
python3 scripts/generate_hospital_data.py

# Start FastAPI backend
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Start React Vite frontend
cd frontend && npm run dev
```

### 3. Run Automated Tests
```bash
python3 -m pytest backend/tests/test_review1.py -v
```

---

## Demo Credentials
- **Chief Admin**: `admin@hospital.com` / `admin123` (Full configuration, experiments, and forecasting access)
- **Staff User**: `staff@hospital.com` / `staff123` (Operational access; configuration modification restricted)

---

## Project Structure
```
coeproj/
├── backend/
│   ├── auth.py               # JWT auth, PBKDF2 hashing, RBAC, tenant isolation
│   ├── database.py           # SQLite connection with WAL mode & page metrics
│   ├── experiments.py        # 3-scenario backtesting simulation engine
│   ├── forecasting.py        # Baseline vs tenant-aware capacity forecasting
│   ├── main.py               # FastAPI application endpoints
│   ├── models.py             # SQLAlchemy models & unique constraints
│   ├── storage_monitor.py    # Table vs index storage & retention projections
│   └── tests/
│       └── test_review1.py   # Automated pytest suite (10/10 passed)
├── frontend/
│   ├── src/
│   │   ├── api.js            # Frontend API client
│   │   ├── App.jsx           # Main React dashboard & review walkthrough
│   │   ├── index.css         # Glassmorphic dark-mode design system
│   │   └── components/
│   │       ├── Charts.jsx    # SVG forecast, storage & retention charts
│   │       └── DemoFlowModal.jsx # Reviewer 5-10 min demo walkthrough modal
├── scripts/
│   └── generate_hospital_data.py # Reproducible data generator (seed=42)
├── docs/
│   └── review1.md            # Formal 25-section Review 1 technical report
├── data/                     # SQLite database file
├── start.sh                  # Application launcher
└── README.md
```

---

## Documentation
For complete architectural diagrams, mathematical formulations, schema specifications, and the **35% Completion Table**, see [`docs/review1.md`](docs/review1.md).
