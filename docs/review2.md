# Review 2 — Next 35% Milestone (70%)

## Delivered in this milestone

This milestone extends the existing Review 1 prototype. It does not replace the SQLite/SQLAlchemy/FastAPI/React architecture.

### 1. Persistent storage snapshots

- Added `storage_snapshots` records for aggregate and tenant-level measurements.
- Admins can capture a snapshot through the API or dashboard.
- A background task records a snapshot every hour by default; configure `STORAGE_SNAPSHOT_INTERVAL_SECONDS` (minimum 60 seconds) for alternate intervals.
- `GET /api/metrics/snapshots` provides history with tenant scoping. Staff see only their own tenant; admins see aggregate history by default or may request an authorized tenant explicitly.
- Each captured cluster snapshot includes modeled storage, quota usage, physical database file size, and table metrics.

### 2. Retention cleanup

- `POST /api/retention/purge?dry_run=true` previews expired appointments and slots by tenant policy.
- `POST /api/retention/purge?dry_run=false` permanently deletes only appointments and slots whose dates are older than that tenant's configured retention cutoff.
- Destructive execution is admin-only and writes `RETENTION_PURGE` audit entries per affected tenant.
- A periodic job runs daily by default. Set `RETENTION_PURGE_ENABLED=false` to disable scheduled deletion and `RETENTION_PURGE_INTERVAL_SECONDS` to change the interval (minimum 60 seconds).
- The scheduler is in-process and single-instance. For multiple app workers or replicas, run the jobs in a dedicated singleton worker or external scheduler to prevent duplicate execution.

### 3. Advanced capacity forecast

`GET /api/forecast/advanced?horizon_days=365` fits a quadratic least-squares trend to up to 90 distinct daily aggregate observations. It first averages snapshots within each day so hourly capture frequency does not distort the fit. It returns the coefficients, trajectory, and projected quota crossing when sufficient history is available.

- Fewer than three distinct days returns `status: insufficient_history` rather than fabricating a prediction.
- Degenerate data returns `status: degenerate_history`.
- Projections are constrained not to decrease due to curve-fit artifacts.
- The output is a statistical prototype forecast, not an operational guarantee; performance must be assessed against historical holdout data before relying on it for capacity procurement.

### 4. Database URL configuration

Set `DATABASE_URL` to a SQLAlchemy URL. SQLite remains the default. PostgreSQL and MySQL dialects are now selectable; their physical database size uses the backend's catalog metrics. The `psycopg[binary]` and `PyMySQL` drivers are included in `requirements.txt`.

This enables connection to those engines, but it does **not** constitute a production migration: schema evolution, transaction/concurrency verification, backups, and engine-specific integration testing remain future work. Existing tables are created with SQLAlchemy `create_all`; no versioned migration system has been added.

## API and demo checklist

1. Start the project with `./start.sh`.
2. Open the admin dashboard and select **Review 2 Operations**.
3. Capture a snapshot; confirm aggregate and per-tenant records are persisted.
4. Query or inspect snapshot history. The advanced fit remains unavailable until snapshots cover at least three distinct dates.
5. Review the retention dry-run counts, then use the explicitly confirmed admin purge only when deletion is intended.
6. Confirm purge counts and `RETENTION_PURGE` records in Audit & Security.
7. Optionally configure an alternate `DATABASE_URL`; validate against a disposable database before using real data.

## Verification

The repository test suite covers the original 10 Review 1 cases plus Review 2 snapshot persistence and tenant scoping, quadratic forecast response, retention dry-run behavior, actual expiry deletion, audit logging, and staff denial of destructive cleanup. Run `python3 -m pytest backend/tests/test_review1.py -q`.

## Explicitly not completed

- ML/ARIMA/Holt-Winters seasonal model validation.
- External email/webhook/Slack alert delivery.
- Multi-worker-safe scheduled jobs / distributed locks.
- PostgreSQL/MySQL deployment and migration test runs against live engines.
- Large-scale concurrency/load testing.
- Docker/Kubernetes production packaging.
- Real stakeholder testing: the existing stakeholder summary is a simulated template, not collected user research.
