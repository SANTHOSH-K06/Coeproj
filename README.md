# Hospital Appointment Capacity Forecasting Engine (Review 2 — 70% Milestone)

A multi-tenant healthcare appointment scheduling and database capacity forecasting prototype. It preserves the Review 1 appointment, tenant isolation, storage monitoring, and forecasting workflows and adds persistent storage history, snapshot-based polynomial forecasting, and policy-driven retention cleanup.

---

## Key Features
1. **Clinical Appointment Workflow**: Multi-tenant appointment booking across Hospital Alpha, Hospital Beta, and Hospital Gamma.
2. **ACID Double-Booking Prevention**: Database-level `UNIQUE(tenant_id, doctor_id, date, slot_time)` constraint preventing concurrent slot collisions with HTTP 409 Conflict.
3. **Role-Based Access Control (RBAC)**: Admin vs Staff roles with JWT authentication, PBKDF2 password hashing, and cross-tenant access denial (`HTTP 403 Forbidden`).
4. **Physical Storage Monitoring**: Direct measurement of SQLite data pages and secondary index pages for `appointments`, `patients`, `doctors`, and `appointment_slots`.
5. **Configurable Retention Rules**: 365-day active retention modeling comparing storage growth with vs without retention.
6. **Dual-Model Capacity Forecasting**:
   - **Baseline Model**: Linear extrapolation based on daily growth rate.
   - **Proposed Model**: Non-linear tenant-weighted model factoring index B-tree overhead, retention damping, confidence score (%), and 95% prediction intervals.
7. **Empirical Backtesting Experiments**: 3 simulated scenarios (Scenario A: Stable growth, Scenario B: Rapid tenant growth, Scenario C: Sudden activity spike) calculating exact forecast error ($\text{ABS}(\text{Predicted} - \text{Actual})$) with 78.3% error reduction.
8. **Persistent Storage History**: Hourly aggregate and per-tenant snapshots, with admin capture and tenant-scoped history API.
9. **Retention Cleanup**: Per-tenant purge preview, admin-confirmed deletion and audit records; scheduled daily cleanup can be disabled by configuration.
10. **Advanced Forecast**: Quadratic least-squares fit to up to 90 distinct daily snapshot observations, with explicit insufficient/degenerate-history states.
11. **Interactive Dashboard**: Existing charts and workflows plus Review 2 snapshot, forecast, and purge operations.

Review 2 implementation details and known limitations are documented in [docs/review2.md](docs/review2.md). The older 35% baseline report remains in [docs/review1.md](docs/review1.md).

---

## Quick Start

### 1. Launch Everything (One Command)
```bash
python3 -m pip install -r requirements.txt
cd frontend && npm install && cd ..
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

## Database and jobs

SQLite is the default. Set `DATABASE_URL` to a SQLAlchemy PostgreSQL or MySQL URL to select another dialect (install the corresponding driver from `requirements.txt`). Validate on a disposable database first; schema migrations and production-engine integration tests are not included yet.

The service captures snapshots hourly and runs the retention purge daily by default. Set `STORAGE_SNAPSHOT_INTERVAL_SECONDS` or `RETENTION_PURGE_INTERVAL_SECONDS` to change intervals (minimum 60 seconds), or set `RETENTION_PURGE_ENABLED=false` to disable the scheduled destructive purge. These jobs run in-process and should be moved to a singleton worker before deploying multiple app replicas.

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
│   ├── storage_history.py    # Persistent snapshots & quadratic forecast
│   ├── retention.py          # Previewable and auditable expiry cleanup
│   ├── jobs.py               # Periodic snapshot and retention jobs
│   └── tests/
│       └── test_review1.py   # Review 1 and Review 2 API coverage
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
│   ├── review1.md            # Review 1 baseline technical report
│   └── review2.md            # Implemented 70% milestone and limitations
├── data/                     # SQLite database file
├── start.sh                  # Application launcher
└── README.md
```

---

## Documentation
For complete architectural diagrams, mathematical formulations, schema specifications, and the **35% Completion Table**, see [`docs/review1.md`](docs/review1.md).
