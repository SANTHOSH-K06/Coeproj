"""Tenant-specific retention previews and historical-record cleanup."""

import datetime
from typing import Any

from sqlalchemy.orm import Session

from .models import Appointment, AppointmentSlot, AuditLog, StorageConfig, Tenant


def purge_expired_records(
    db: Session,
    *,
    dry_run: bool = True,
    now: datetime.date | None = None,
    actor_email: str = "retention-scheduler",
) -> dict[str, Any]:
    """Preview or remove appointments and slots older than each tenant's policy.

    Audit logs, patients, doctors, and future appointments are intentionally retained.
    """
    today = now or datetime.date.today()
    results = []
    total_appointments = 0
    total_slots = 0

    for tenant in db.query(Tenant).order_by(Tenant.id).all():
        config = db.query(StorageConfig).filter(StorageConfig.tenant_id == tenant.id).first()
        retention_days = config.retention_days if config else 365
        cutoff = (today - datetime.timedelta(days=retention_days)).isoformat()
        appointment_query = db.query(Appointment).filter(
            Appointment.tenant_id == tenant.id,
            Appointment.date < cutoff,
        )
        slot_query = db.query(AppointmentSlot).filter(
            AppointmentSlot.tenant_id == tenant.id,
            AppointmentSlot.date < cutoff,
        )
        appointment_count = appointment_query.count()
        slot_count = slot_query.count()
        total_appointments += appointment_count
        total_slots += slot_count
        results.append({
            "tenant_id": tenant.id,
            "tenant_name": tenant.name,
            "retention_days": retention_days,
            "cutoff_date_exclusive": cutoff,
            "expired_appointments": appointment_count,
            "expired_slots": slot_count,
        })
        if not dry_run and (appointment_count or slot_count):
            appointment_query.delete(synchronize_session=False)
            slot_query.delete(synchronize_session=False)
            db.add(AuditLog(
                tenant_id=tenant.id,
                user_email=actor_email,
                action="RETENTION_PURGE",
                status="SUCCESS",
                details=(
                    f"Removed {appointment_count} appointments and {slot_count} slots "
                    f"dated before {cutoff} under the {retention_days}-day policy."
                ),
            ))

    if not dry_run:
        db.commit()

    return {
        "dry_run": dry_run,
        "as_of_date": today.isoformat(),
        "tenants": results,
        "expired_appointments": total_appointments,
        "expired_slots": total_slots,
        "deleted_appointments": 0 if dry_run else total_appointments,
        "deleted_slots": 0 if dry_run else total_slots,
    }
