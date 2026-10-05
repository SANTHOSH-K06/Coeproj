# Changelog

## 2026-10-05 — Review 2 / 70% milestone

- Preserved the existing Review 1 hospital scheduling, tenant isolation, audit, storage-monitoring, and forecast workflows.
- Added persistent cluster and tenant storage snapshots, an hourly background capture job, and authenticated snapshot-history endpoints.
- Added admin-only retention preview and audited deletion for expired appointments and slots, plus a configurable daily job.
- Added a quadratic capacity trend forecast based on distinct daily snapshots, including explicit insufficient/degenerate-history responses.
- Added the Review 2 Operations dashboard view for capturing snapshots, viewing history, inspecting forecast status, and previewing/executing cleanup.
- Added SQLAlchemy `DATABASE_URL` dialect selection for SQLite, PostgreSQL, and MySQL; blocked the destructive demo reset for non-SQLite databases.
- Added Review 2 API tests and updated project setup and milestone documentation.
- Corrected stakeholder-validation notes: real stakeholder sessions have not yet taken place.

### Verification

- `python3 -m pytest backend/tests/test_review1.py -q` — 13 passed.
- `npm run build` in `frontend/` — production build succeeded.
- Local dashboard and API were started; manual snapshot capture returned four records (one cluster and three tenant snapshots).

### Known limitations

- PostgreSQL/MySQL were not integration-tested; this is dialect/configuration support, not production certification.
- The scheduler runs in-process and requires a singleton worker or external scheduler for multi-replica deployment.
- The quadratic model requires at least three distinct days and has not been validated against holdout data.
- No production schema migration tool, real user evaluation, external alert delivery, load testing, or production deployment packaging is included.
