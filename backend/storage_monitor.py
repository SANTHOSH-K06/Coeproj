import os
import datetime
from typing import Dict, List, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from .database import DB_PATH, get_db_file_metrics
from .models import Tenant, Appointment, Patient, Doctor, AppointmentSlot, StorageConfig

# Schema specification for physical storage modeling (bytes per row and index entry)
TABLE_SPECS = {
    "appointments": {
        "model": Appointment,
        "avg_row_bytes": 288,   # id, tenant_id, doctor_id, patient_id, date, slot_time, reason, status, timestamp, row headers
        "index_specs": [
            {"name": "pk_appointments", "key_bytes": 16},
            {"name": "uq_appointment_doctor_slot", "key_bytes": 64},
            {"name": "ix_appointment_tenant_date", "key_bytes": 32},
        ]
    },
    "patients": {
        "model": Patient,
        "avg_row_bytes": 192,
        "index_specs": [
            {"name": "pk_patients", "key_bytes": 16},
            {"name": "ix_patient_tenant_mrn", "key_bytes": 40},
        ]
    },
    "doctors": {
        "model": Doctor,
        "avg_row_bytes": 160,
        "index_specs": [
            {"name": "pk_doctors", "key_bytes": 16},
            {"name": "ix_doctor_tenant_name", "key_bytes": 48},
        ]
    },
    "appointment_slots": {
        "model": AppointmentSlot,
        "avg_row_bytes": 128,
        "index_specs": [
            {"name": "pk_slots", "key_bytes": 16},
            {"name": "uq_slot_tenant_doctor_date_time", "key_bytes": 64},
        ]
    }
}

PAGE_SIZE = 4096  # SQLite default B-Tree page size

def calculate_table_metrics(db: Session) -> Dict[str, Any]:
    """Calculate granular storage metrics for core tables and their indexes."""
    table_metrics = []
    total_data_bytes = 0
    total_index_bytes = 0
    
    file_metrics = get_db_file_metrics()
    
    for table_name, spec in TABLE_SPECS.items():
        row_count = db.query(spec["model"]).count()
        
        # Data page calculation (including SQLite page header overhead)
        usable_page_bytes = PAGE_SIZE - 64
        rows_per_page = max(1, usable_page_bytes // spec["avg_row_bytes"])
        data_pages = (row_count + rows_per_page - 1) // rows_per_page if row_count > 0 else 1
        data_bytes = data_pages * PAGE_SIZE
        
        # Index calculation across all indexes on the table
        table_idx_bytes = 0
        for idx in spec["index_specs"]:
            # B-tree interior + leaf nodes overhead
            entries_per_page = max(1, usable_page_bytes // (idx["key_bytes"] + 12))
            idx_pages = (row_count + entries_per_page - 1) // entries_per_page if row_count > 0 else 1
            table_idx_bytes += (idx_pages * PAGE_SIZE)
            
        total_data_bytes += data_bytes
        total_index_bytes += table_idx_bytes
        
        table_metrics.append({
            "table_name": table_name,
            "rows": row_count,
            "table_size_bytes": data_bytes,
            "table_size_kb": round(data_bytes / 1024, 2),
            "index_size_bytes": table_idx_bytes,
            "index_size_kb": round(table_idx_bytes / 1024, 2),
            "total_size_bytes": data_bytes + table_idx_bytes,
            "total_size_kb": round((data_bytes + table_idx_bytes) / 1024, 2)
        })
        
    return {
        "tables": table_metrics,
        "total_data_kb": round(total_data_bytes / 1024, 2),
        "total_index_kb": round(total_index_bytes / 1024, 2),
        "physical_db_size_kb": round(file_metrics["file_size_bytes"] / 1024, 2),
        "page_size": file_metrics["page_size"],
        "page_count": file_metrics["page_count"],
        "freelist_count": file_metrics["freelist_count"]
    }

def get_tenant_storage_breakdown(db: Session) -> List[Dict[str, Any]]:
    """Compute tenant-aware storage footprint and growth rate."""
    tenants = db.query(Tenant).all()
    results = []
    
    # Baseline growth rate profiles (MB/day)
    GROWTH_MAP = {
        "high": 0.45,    # Hospital Alpha: ~450 KB/day
        "medium": 0.20,  # Hospital Beta:  ~200 KB/day
        "low": 0.08      # Hospital Gamma: ~80 KB/day
    }
    
    for tenant in tenants:
        appt_count = db.query(Appointment).filter(Appointment.tenant_id == tenant.id).count()
        patient_count = db.query(Patient).filter(Patient.tenant_id == tenant.id).count()
        doctor_count = db.query(Doctor).filter(Doctor.tenant_id == tenant.id).count()
        slot_count = db.query(AppointmentSlot).filter(AppointmentSlot.tenant_id == tenant.id).count()
        
        total_rows = appt_count + patient_count + doctor_count + slot_count
        
        # Estimate storage for this tenant
        est_data_bytes = (
            appt_count * TABLE_SPECS["appointments"]["avg_row_bytes"] +
            patient_count * TABLE_SPECS["patients"]["avg_row_bytes"] +
            doctor_count * TABLE_SPECS["doctors"]["avg_row_bytes"] +
            slot_count * TABLE_SPECS["appointment_slots"]["avg_row_bytes"]
        )
        
        # Estimate index overhead for this tenant (~40% of data size)
        est_index_bytes = int(est_data_bytes * 0.42)
        total_bytes = est_data_bytes + est_index_bytes
        
        config = db.query(StorageConfig).filter(StorageConfig.tenant_id == tenant.id).first()
        storage_limit_mb = config.max_storage_mb if config else 25.0
        retention_days = config.retention_days if config else 365
        
        storage_mb = total_bytes / (1024 * 1024)
        usage_pct = min(100.0, (storage_mb / storage_limit_mb) * 100.0) if storage_limit_mb > 0 else 0.0
        
        growth_rate = GROWTH_MAP.get(tenant.growth_rate_profile, 0.15)
        
        results.append({
            "tenant_id": tenant.id,
            "code": tenant.code,
            "name": tenant.name,
            "profile": tenant.growth_rate_profile,
            "appointment_count": appt_count,
            "patient_count": patient_count,
            "doctor_count": doctor_count,
            "slot_count": slot_count,
            "total_rows": total_rows,
            "table_size_kb": round(est_data_bytes / 1024, 2),
            "index_size_kb": round(est_index_bytes / 1024, 2),
            "total_storage_kb": round(total_bytes / 1024, 2),
            "total_storage_mb": round(storage_mb, 3),
            "growth_rate_mb_day": growth_rate,
            "storage_limit_mb": storage_limit_mb,
            "retention_days": retention_days,
            "usage_percent": round(usage_pct, 2)
        })
        
    return results

def get_retention_comparison(db: Session, projection_days: int = 180) -> Dict[str, Any]:
    """
    Project storage growth comparing:
    1. WITHOUT Retention (historical records accumulate forever)
    2. WITH Retention (records older than retention_days are purged)
    """
    tenants = db.query(Tenant).all()
    today = datetime.date.today()
    
    # Calculate baseline total current storage and daily growth across tenants
    tenant_breakdown = get_tenant_storage_breakdown(db)
    current_storage_mb = sum(t["total_storage_mb"] for t in tenant_breakdown)
    daily_growth_mb = sum(t["growth_rate_mb_day"] for t in tenant_breakdown)
    
    # Average retention rule across tenants
    configs = db.query(StorageConfig).all()
    avg_retention_days = int(sum(c.retention_days for c in configs) / len(configs)) if configs else 365
    
    points_without_retention = []
    points_with_retention = []
    
    # Step intervals (every 15 days)
    for day in range(0, projection_days + 1, 15):
        target_date = (today + datetime.timedelta(days=day)).strftime("%Y-%m-%d")
        
        # Unbounded accumulation
        storage_no_retention = current_storage_mb + (day * daily_growth_mb)
        
        # Retention curve: once history reaches retention limit, daily additions are offset by daily purges
        # Within the 365 day window, active storage grows; retention caps the max historical footprint
        retention_factor = max(0.4, 1.0 - (day / (avg_retention_days * 1.5)))
        storage_with_retention = current_storage_mb + (day * daily_growth_mb * retention_factor)
        
        points_without_retention.append({
            "day": day,
            "date": target_date,
            "storage_mb": round(storage_no_retention, 2)
        })
        points_with_retention.append({
            "day": day,
            "date": target_date,
            "storage_mb": round(storage_with_retention, 2)
        })
        
    storage_savings_mb = round(points_without_retention[-1]["storage_mb"] - points_with_retention[-1]["storage_mb"], 2)
    
    return {
        "avg_retention_days": avg_retention_days,
        "current_storage_mb": round(current_storage_mb, 3),
        "daily_growth_mb": round(daily_growth_mb, 3),
        "projection_days": projection_days,
        "without_retention": points_without_retention,
        "with_retention": points_with_retention,
        "storage_savings_mb": storage_savings_mb,
        "savings_percent": round((storage_savings_mb / points_without_retention[-1]["storage_mb"]) * 100, 1) if points_without_retention[-1]["storage_mb"] > 0 else 0
    }
