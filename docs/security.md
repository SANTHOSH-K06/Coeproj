# Security and Misuse Resistance

## Authentication and authorization

- PBKDF2 password hashing for stored credentials.
- JWT-based session control with bearer authentication.
- Role separation between `admin` and `staff`.
- Tenant-scoped access enforcement before appointment, forecast, and configuration endpoints become active.

## Cross-tenant controls

The backend enforces tenant boundaries through `verify_tenant_access`. Any attempt to access another tenant's data is logged as `CROSS_TENANT_ACCESS_ATTEMPT` and returns `403 Forbidden`. Audit entries are application-level records in the same database; they are not tamper-proof or immutable against database administrators.

## Double-booking controls

The critical clinic safety measure is the database unique constraint on appointments. Even if two requests arrive concurrently, only one row can survive. The rejected request receives `HTTP 409` and an audit event.

## Config guardrails

Admins can change retention and storage limits, but configuration endpoints enforce minimum values and reject invalid input. Staff users cannot change policy settings. This preserves operational control and reduces accidental misconfiguration.

## Audit logging coverage

The project records login attempts, appointment creation, appointment rejection, configuration changes, and cross-tenant access blocks. This provides reviewable evidence for operations and incident review.

## Security posture summary

The prototype deliberately fails closed: invalid credentials are rejected, unauthorized access is denied with a generic 401/403 response, and suspicious access attempts are logged. This is appropriate for a field-ready hospital workflow prototype where safety and mis-use resistance matter more than convenience.
