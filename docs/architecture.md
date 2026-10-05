# Architecture

## Overview
The project is a multi-tenant hospital appointment and capacity forecasting system built around a FastAPI backend, SQLite data layer, and Vite-based front-end dashboard. The current implementation reflects the approved Review 1 milestone and preserves the core workflow: user authentication, role-based access control, tenant isolation, appointment booking, storage monitoring, and capacity forecasting.

## Major components

- Frontend: React + Vite dashboard for login, booking, config, and forecast visualization.
- Backend API: FastAPI endpoints for authentication, tenant access, appointment creation, storage metrics, retention, configuration, forecast generation, and experiments.
- Persistence: SQLAlchemy models for tenants, users, doctors, patients, appointment slots, appointments, storage configs, and audit logs.
- Forecast engine: baseline linear forecast vs tenant-aware proposed model.
- Security layer: JWT authentication, PBKDF2 hashing, RBAC checks, and cross-tenant denial.
- Audit & compliance: audit log entries for login success/failure, configuration changes, booking events, and attempted breaches.

## Data flow

1. User authenticates through `/api/auth/login`.
2. JWT payload contains tenant and role metadata.
3. Protected API calls validate the token and tenant membership.
4. Appointment booking uses a database-level unique constraint to reject duplicate slots.
5. Storage metrics are computed from SQLite table/page structure and tenant configuration.
6. Forecasting compares baseline and tenant-aware model outputs and exposes the results through the dashboard.

## Tenant boundary model
Each user is tied to a tenant. The `verify_tenant_access` check blocks cross-tenant reads, writes, or configuration changes unless the user is the correct tenant owner or an admin. This preserves multi-tenant isolation even in the presence of malicious or misconfigured access.

## Database protections
The appointment model includes a unique constraint across `tenant_id`, `doctor_id`, `date`, and `slot_time`. This is the critical ACID-level protection against double-booking and is enforced before data is saved.

## Forecasting architecture
The storage and forecasting pipeline uses: current tenant storage, storage config, retention window, growth profile, index overhead estimation, and predictive simulation. The baseline model uses average daily growth, while the proposed model weights tenant growth profile and retention effects to improve accuracy.

## Production readiness notes
The project is a field-ready prototype, not a full enterprise deployment. It demonstrates the core hospital operations and forecasting workflow correctly and is structured for extension to PostgreSQL or a larger multi-service architecture.
