import os
import datetime
from contextlib import asynccontextmanager
from typing import AsyncIterator
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .database import get_db, Base, engine
from .models import Tenant, User, Doctor, Patient, AppointmentSlot, Appointment, StorageConfig, AuditLog, StorageSnapshot
from .auth import (
    hash_password, verify_password, create_access_token, 
    get_current_user, require_admin, verify_tenant_access
)
from .storage_monitor import (
    calculate_table_metrics, get_tenant_storage_breakdown, get_retention_comparison
)
from .forecasting import (
    run_baseline_forecast, run_proposed_forecast, generate_forecast_trajectories
)
from .experiments import run_all_scenarios
from .storage_history import capture_storage_snapshot, polynomial_storage_forecast
from .retention import purge_expired_records
from .jobs import start_background_jobs, stop_background_jobs
from scripts.generate_hospital_data import generate_data

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(bind=engine)
    jobs = start_background_jobs()
    try:
        yield
    finally:
        await stop_background_jobs(jobs)

app = FastAPI(
    title="Hospital Capacity Forecasting API",
    description="Multi-tenant hospital appointment management with persistent storage history, retention operations, and capacity forecasting (Review 2 - 70% Milestone)",
    version="0.70.0",
    lifespan=lifespan,
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- Pydantic Schemas -----------------

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

class AppointmentCreate(BaseModel):
    tenant_id: int
    doctor_id: int
    patient_id: int
    date: str = Field(..., description="YYYY-MM-DD")
    slot_time: str = Field(..., description="e.g. 10:00 AM")
    reason: Optional[str] = "General Consultation"

class StorageConfigUpdate(BaseModel):
    max_storage_mb: float = Field(..., gt=0.1, le=1000.0, description="Storage limit in MB (must be > 0.1)")
    retention_days: int = Field(..., ge=30, le=3650, description="Retention window in days (must be >= 30)")

# ----------------- Auth Endpoints -----------------

@app.post("/api/auth/login", response_model=LoginResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        # Audit failed login attempt
        log = AuditLog(
            tenant_id=user.tenant_id if user else None,
            user_email=req.email,
            action="LOGIN_FAILED",
            status="REJECTED",
            details="Invalid email or password credentials provided."
        )
        db.add(log)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password credentials."
        )
        
    token = create_access_token(data={"sub": user.email, "role": user.role, "tenant_id": user.tenant_id})
    
    # Audit successful login
    log = AuditLog(
        tenant_id=user.tenant_id,
        user_email=user.email,
        action="LOGIN_SUCCESS",
        status="SUCCESS",
        details=f"User {user.email} authenticated successfully with role '{user.role}'."
    )
    db.add(log)
    db.commit()
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "tenant_id": user.tenant_id
        }
    }

@app.get("/api/auth/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role,
        "tenant_id": current_user.tenant_id
    }

# ----------------- Tenant Endpoints -----------------

@app.get("/api/tenants")
def list_tenants(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    tenants = db.query(Tenant).all()
    return tenants

@app.get("/api/tenants/{tenant_id}")
def get_tenant(tenant_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    verify_tenant_access(current_user, tenant_id, db)
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant

# ----------------- Doctors & Patients Endpoints -----------------

@app.get("/api/doctors")
def list_doctors(tenant_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Doctor)
    if tenant_id:
        verify_tenant_access(current_user, tenant_id, db)
        query = query.filter(Doctor.tenant_id == tenant_id)
    elif current_user.role != "admin" and current_user.tenant_id:
        query = query.filter(Doctor.tenant_id == current_user.tenant_id)
    return query.all()

@app.get("/api/patients")
def list_patients(tenant_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Patient)
    if tenant_id:
        verify_tenant_access(current_user, tenant_id, db)
        query = query.filter(Patient.tenant_id == tenant_id)
    elif current_user.role != "admin" and current_user.tenant_id:
        query = query.filter(Patient.tenant_id == current_user.tenant_id)
    return query.all()

# ----------------- Appointment Endpoints & Double-Booking Prevention -----------------

@app.get("/api/appointments")
def list_appointments(
    tenant_id: Optional[int] = None, 
    date: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    query = db.query(Appointment)
    if tenant_id:
        verify_tenant_access(current_user, tenant_id, db)
        query = query.filter(Appointment.tenant_id == tenant_id)
    elif current_user.role != "admin" and current_user.tenant_id:
        query = query.filter(Appointment.tenant_id == current_user.tenant_id)
        
    if date:
        query = query.filter(Appointment.date == date)
        
    appts = query.order_by(Appointment.date.desc(), Appointment.id.desc()).limit(limit).all()
    
    # Enrich with doctor and patient details
    results = []
    for a in appts:
        results.append({
            "id": a.id,
            "tenant_id": a.tenant_id,
            "tenant_name": a.tenant.name if a.tenant else f"Tenant {a.tenant_id}",
            "doctor_id": a.doctor_id,
            "doctor_name": a.doctor.name if a.doctor else "Unknown Doctor",
            "patient_id": a.patient_id,
            "patient_name": a.patient.name if a.patient else "Unknown Patient",
            "date": a.date,
            "slot_time": a.slot_time,
            "reason": a.reason,
            "status": a.status,
            "created_at": a.created_at.isoformat() if a.created_at else None
        })
    return results

@app.post("/api/appointments")
def create_appointment(
    req: AppointmentCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Attempt to book an appointment.
    ENFORCES DATABASE-LEVEL DOUBLE-BOOKING PREVENTION via UniqueConstraint on
    (tenant_id, doctor_id, date, slot_time).
    """
    verify_tenant_access(current_user, req.tenant_id, db)
    
    # Validate Doctor & Patient exist in tenant
    doctor = db.query(Doctor).filter(Doctor.id == req.doctor_id, Doctor.tenant_id == req.tenant_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found in this hospital")
        
    patient = db.query(Patient).filter(Patient.id == req.patient_id, Patient.tenant_id == req.tenant_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found in this hospital")

    new_appt = Appointment(
        tenant_id=req.tenant_id,
        doctor_id=req.doctor_id,
        patient_id=req.patient_id,
        date=req.date,
        slot_time=req.slot_time,
        reason=req.reason or "General Consultation",
        status="CONFIRMED"
    )

    try:
        db.add(new_appt)
        db.commit()
        db.refresh(new_appt)
        
        # Log successful appointment
        log = AuditLog(
            tenant_id=req.tenant_id,
            user_email=current_user.email,
            action="APPOINTMENT_BOOKED",
            status="SUCCESS",
            details=f"Booked slot for {patient.name} with {doctor.name} on {req.date} at {req.slot_time}."
        )
        db.add(log)
        db.commit()
        
        return {
            "success": True,
            "message": "Appointment successfully booked.",
            "appointment": {
                "id": new_appt.id,
                "tenant_id": new_appt.tenant_id,
                "doctor_name": doctor.name,
                "patient_name": patient.name,
                "date": new_appt.date,
                "slot_time": new_appt.slot_time,
                "status": new_appt.status
            }
        }
        
    except IntegrityError as ie:
        db.rollback()
        # Database-level unique constraint failed!
        log = AuditLog(
            tenant_id=req.tenant_id,
            user_email=current_user.email,
            action="DOUBLE_BOOKING_PREVENTED",
            status="REJECTED",
            details=f"Database-level conflict: doctor {doctor.name} already booked on {req.date} at {req.slot_time}."
        )
        db.add(log)
        db.commit()
        
        # Exact message required for Review 1 specification:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Appointment slot already booked."
        )

# ----------------- Storage Monitoring & Retention -----------------

@app.get("/api/metrics/storage")
def get_storage_metrics(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    table_metrics = calculate_table_metrics(db)
    tenant_breakdown = get_tenant_storage_breakdown(db)
    
    total_rows = sum(t["total_rows"] for t in tenant_breakdown)
    total_storage_mb = sum(t["total_storage_mb"] for t in tenant_breakdown)
    
    configs = db.query(StorageConfig).all()
    storage_limit_mb = sum(c.max_storage_mb for c in configs) if configs else 75.0
    usage_pct = round((total_storage_mb / storage_limit_mb) * 100.0, 2) if storage_limit_mb > 0 else 0
    daily_growth_mb = round(sum(t["growth_rate_mb_day"] for t in tenant_breakdown), 3)

    return {
        "overall": {
            "total_rows": total_rows,
            "total_storage_mb": round(total_storage_mb, 3),
            "storage_limit_mb": round(storage_limit_mb, 2),
            "usage_percent": usage_pct,
            "daily_growth_mb": daily_growth_mb,
            "physical_db_size_kb": table_metrics["physical_db_size_kb"],
            "page_size": table_metrics["page_size"],
            "page_count": table_metrics["page_count"]
        },
        "tables": table_metrics["tables"],
        "tenants": tenant_breakdown
    }

@app.get("/api/metrics/retention")
def get_retention_metrics(
    days: int = Query(180, ge=30, le=730),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_retention_comparison(db, projection_days=days)

@app.post("/api/metrics/snapshots")
def create_storage_snapshot(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    rows = capture_storage_snapshot(db)
    return {
        "success": True,
        "captured_at": rows[0].captured_at.isoformat(),
        "snapshots_created": len(rows),
        "storage_mb": rows[0].storage_mb,
        "storage_limit_mb": rows[0].storage_limit_mb,
    }

@app.get("/api/metrics/snapshots")
def list_storage_snapshots(
    tenant_id: Optional[int] = None,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(StorageSnapshot)
    if tenant_id is not None:
        verify_tenant_access(current_user, tenant_id, db)
        query = query.filter(StorageSnapshot.tenant_id == tenant_id)
    elif current_user.role == "admin":
        query = query.filter(StorageSnapshot.tenant_id.is_(None))
    else:
        query = query.filter(StorageSnapshot.tenant_id == current_user.tenant_id)
    snapshots = query.order_by(StorageSnapshot.captured_at.desc()).limit(limit).all()
    return [
        {
            "id": snapshot.id,
            "tenant_id": snapshot.tenant_id,
            "captured_at": snapshot.captured_at.isoformat(),
            "storage_mb": snapshot.storage_mb,
            "storage_limit_mb": snapshot.storage_limit_mb,
            "usage_percent": snapshot.usage_percent,
            "physical_db_size_kb": snapshot.physical_db_size_kb,
            "table_metrics": snapshot.table_metrics,
        }
        for snapshot in snapshots
    ]

@app.get("/api/forecast/advanced")
def get_advanced_forecast(
    horizon_days: int = Query(365, ge=30, le=1825),
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    configs = db.query(StorageConfig).all()
    limit_mb = sum(config.max_storage_mb for config in configs) if configs else 75.0
    return polynomial_storage_forecast(db, limit_mb, horizon_days=horizon_days)

@app.post("/api/retention/purge")
def run_retention_purge(
    dry_run: bool = Query(True),
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    return purge_expired_records(
        db,
        dry_run=dry_run,
        actor_email=admin_user.email,
    )

# ----------------- Config Endpoints (Admin Only) -----------------

@app.put("/api/config/tenant/{tenant_id}")
def update_tenant_storage_config(
    tenant_id: int,
    config_update: StorageConfigUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    # Validation: storage limit must be valid
    if config_update.max_storage_mb <= 0:
        raise HTTPException(status_code=400, detail="Invalid storage configuration: Storage limit must be greater than 0.")
    if config_update.retention_days < 30:
        raise HTTPException(status_code=400, detail="Invalid retention value: Minimum retention window is 30 days.")

    config = db.query(StorageConfig).filter(StorageConfig.tenant_id == tenant_id).first()
    if not config:
        config = StorageConfig(
            tenant_id=tenant_id,
            max_storage_mb=config_update.max_storage_mb,
            retention_days=config_update.retention_days
        )
        db.add(config)
    else:
        config.max_storage_mb = config_update.max_storage_mb
        config.retention_days = config_update.retention_days
        
    # Audit configuration change
    log = AuditLog(
        tenant_id=tenant_id,
        user_email=admin_user.email,
        action="CONFIG_UPDATED",
        status="SUCCESS",
        details=f"Admin {admin_user.email} updated Tenant {tenant_id} config: Limit={config_update.max_storage_mb}MB, Retention={config_update.retention_days} days."
    )
    db.add(log)
    db.commit()
    db.refresh(config)

    return {
        "success": True,
        "tenant_id": tenant_id,
        "max_storage_mb": config.max_storage_mb,
        "retention_days": config.retention_days
    }

# ----------------- Capacity Forecasting -----------------

@app.get("/api/forecast")
def get_forecast(
    spike_multiplier: float = Query(1.0, ge=0.5, le=5.0),
    days_ahead: int = Query(120, ge=30, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return generate_forecast_trajectories(
        db, 
        days_ahead=days_ahead, 
        sudden_spike_multiplier=spike_multiplier
    )

# ----------------- Experiments Engine -----------------

@app.post("/api/experiments/run")
def run_experiments(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    results = run_all_scenarios(db, seed=42)
    
    # Audit experiment run
    log = AuditLog(
        tenant_id=None,
        user_email=admin_user.email,
        action="EXPERIMENT_RUN",
        status="SUCCESS",
        details="Executed 3-scenario capacity forecasting backtesting experiment."
    )
    db.add(log)
    db.commit()
    
    return results

# ----------------- Security Demos & Failure Cases -----------------

@app.post("/api/demo/cross-tenant-test")
def trigger_cross_tenant_test(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Attempt cross-tenant breach explicitly to demonstrate security rejection & logging."""
    target_tenant_id = 2 if current_user.tenant_id == 1 else 1
    
    log = AuditLog(
        tenant_id=target_tenant_id,
        user_email=current_user.email,
        action="CROSS_TENANT_BREACH_ATTEMPT",
        status="ACCESS DENIED",
        details=f"SECURITY ALERT: User {current_user.email} (Tenant {current_user.tenant_id}) attempted unauthorized cross-tenant read on Tenant {target_tenant_id}."
    )
    db.add(log)
    db.commit()
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="ACCESS DENIED: Cross-tenant data isolation violation."
    )

@app.get("/api/audit-logs")
def get_audit_logs(
    limit: int = 50,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
    return [
        {
            "id": l.id,
            "tenant_id": l.tenant_id,
            "user_email": l.user_email,
            "action": l.action,
            "status": l.status,
            "details": l.details,
            "created_at": l.created_at.isoformat() if l.created_at else None
        }
        for l in logs
    ]

@app.post("/api/demo/reset")
def reset_demo_database(
    admin_user: User = Depends(require_admin)
):
    """Re-seed the synthetic dataset to baseline state."""
    if engine.dialect.name != "sqlite":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Demo reset is disabled for non-SQLite databases because the synthetic seeder recreates tables.",
        )
    generate_data()
    return {"success": True, "message": "Demo database successfully reset to baseline synthetic state."}
