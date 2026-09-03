import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base, get_db
from backend.main import app
from backend.models import Tenant, User, Doctor, Patient, Appointment, StorageConfig, AuditLog
from backend.auth import hash_password, create_access_token

# Test database
TEST_DB = "test_hospital.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{TEST_DB}"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    # 1. Seed Tenants
    alpha = Tenant(code="ALPHA", name="Hospital Alpha", growth_rate_profile="high")
    beta = Tenant(code="BETA", name="Hospital Beta", growth_rate_profile="medium")
    gamma = Tenant(code="GAMMA", name="Hospital Gamma", growth_rate_profile="low")
    db.add_all([alpha, beta, gamma])
    db.commit()

    # 2. Seed Storage Config
    for t in [alpha, beta, gamma]:
        db.add(StorageConfig(tenant_id=t.id, max_storage_mb=25.0, retention_days=365))
    db.commit()

    # 3. Seed Users
    admin_user = User(
        tenant_id=alpha.id,
        email="admin@hospital.com",
        password_hash=hash_password("admin123"),
        name="Chief Admin",
        role="admin"
    )
    staff_user = User(
        tenant_id=alpha.id,
        email="staff@hospital.com",
        password_hash=hash_password("staff123"),
        name="Staff User",
        role="staff"
    )
    staff_beta = User(
        tenant_id=beta.id,
        email="staff.beta@hospital.com",
        password_hash=hash_password("staff123"),
        name="Staff Beta",
        role="staff"
    )
    db.add_all([admin_user, staff_user, staff_beta])
    db.commit()

    # 4. Seed Doctors & Patients
    dr_demo = Doctor(tenant_id=alpha.id, name="Dr. Demo", specialty="Cardiology", room_number="101")
    db.add(dr_demo)
    db.commit()

    pt_a = Patient(tenant_id=alpha.id, name="Patient A", medical_record_num="MRN-001")
    pt_b = Patient(tenant_id=alpha.id, name="Patient B", medical_record_num="MRN-002")
    db.add_all([pt_a, pt_b])
    db.commit()
    
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

# ----------------- Review 1 Tests -----------------

def test_1_authentication_and_roles():
    """Verify demo accounts work and return correct roles."""
    # Admin login
    res = client.post("/api/auth/login", json={"email": "admin@hospital.com", "password": "admin123"})
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["role"] == "admin"
    assert "access_token" in data

    # Staff login
    res = client.post("/api/auth/login", json={"email": "staff@hospital.com", "password": "staff123"})
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["role"] == "staff"

    # Invalid login
    res = client.post("/api/auth/login", json={"email": "admin@hospital.com", "password": "wrong"})
    assert res.status_code == 401

def test_2_appointment_booking_and_double_booking_prevention():
    """
    Review 1 Demo Flow:
    1. Admin/Staff logs in.
    2. Select Hospital Alpha, Dr. Demo, Date, 10:00 AM, Book Patient A -> SUCCESS.
    3. Immediately attempt Patient B, same tenant, doctor, date, time -> REJECTED.
    4. Verify message: 'Appointment slot already booked.'
    5. Verify database contains only 1 record.
    """
    login_res = client.post("/api/auth/login", json={"email": "admin@hospital.com", "password": "admin123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Step 1: Book Patient A
    payload_a = {
        "tenant_id": 1,
        "doctor_id": 1,
        "patient_id": 1,
        "date": "2026-10-15",
        "slot_time": "10:00 AM",
        "reason": "Cardiology Consultation"
    }
    res_a = client.post("/api/appointments", json=payload_a, headers=headers)
    assert res_a.status_code == 200
    assert res_a.json()["success"] is True

    # Step 2: Attempt Patient B on same slot
    payload_b = {
        "tenant_id": 1,
        "doctor_id": 1,
        "patient_id": 2,
        "date": "2026-10-15",
        "slot_time": "10:00 AM",
        "reason": "Emergency Consultation"
    }
    res_b = client.post("/api/appointments", json=payload_b, headers=headers)
    assert res_b.status_code == 409
    assert res_b.json()["detail"] == "Appointment slot already booked."

    # Step 3: Verify only 1 record in database
    db = TestingSessionLocal()
    appts = db.query(Appointment).filter(
        Appointment.tenant_id == 1,
        Appointment.doctor_id == 1,
        Appointment.date == "2026-10-15",
        Appointment.slot_time == "10:00 AM"
    ).all()
    assert len(appts) == 1
    assert appts[0].patient_id == 1
    db.close()

def test_3_tenant_isolation_and_cross_tenant_denial():
    """Attempt cross-tenant access by staff and verify ACCESS DENIED + audit log."""
    # Login as Staff of Hospital Beta
    login_res = client.post("/api/auth/login", json={"email": "staff.beta@hospital.com", "password": "staff123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Hospital Beta staff tries to book in Hospital Alpha (tenant_id=1)
    payload = {
        "tenant_id": 1,
        "doctor_id": 1,
        "patient_id": 1,
        "date": "2026-10-16",
        "slot_time": "11:00 AM"
    }
    res = client.post("/api/appointments", json=payload, headers=headers)
    assert res.status_code == 403
    assert "ACCESS DENIED" in res.json()["detail"]

    # Verify audit log recorded violation
    db = TestingSessionLocal()
    log = db.query(AuditLog).filter(
        AuditLog.user_email == "staff.beta@hospital.com",
        AuditLog.status == "ACCESS DENIED"
    ).first()
    assert log is not None
    assert "CROSS_TENANT" in log.action
    db.close()

def test_4_rbac_staff_cannot_change_configuration():
    """Staff cannot change storage limit or retention (returns 403)."""
    login_res = client.post("/api/auth/login", json={"email": "staff@hospital.com", "password": "staff123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    config_payload = {"max_storage_mb": 50.0, "retention_days": 180}
    res = client.put("/api/config/tenant/1", json=config_payload, headers=headers)
    assert res.status_code == 403
    assert "Admin privileges required" in res.json()["detail"]

def test_5_admin_can_update_configuration_with_validation():
    """Admin can update configuration, but invalid limits/retention values are rejected."""
    login_res = client.post("/api/auth/login", json={"email": "admin@hospital.com", "password": "admin123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Valid update
    valid_payload = {"max_storage_mb": 35.0, "retention_days": 180}
    res = client.put("/api/config/tenant/1", json=valid_payload, headers=headers)
    assert res.status_code == 200
    assert res.json()["max_storage_mb"] == 35.0
    assert res.json()["retention_days"] == 180

    # Invalid storage limit (negative or 0)
    res_bad_storage = client.put("/api/config/tenant/1", json={"max_storage_mb": -5.0, "retention_days": 180}, headers=headers)
    assert res_bad_storage.status_code == 422 or res_bad_storage.status_code == 400

    # Invalid retention window (< 30 days)
    res_bad_retention = client.put("/api/config/tenant/1", json={"max_storage_mb": 35.0, "retention_days": 5}, headers=headers)
    assert res_bad_retention.status_code == 422 or res_bad_retention.status_code == 400

def test_6_storage_monitoring_metrics():
    """Verify table and index metrics are tracked."""
    login_res = client.post("/api/auth/login", json={"email": "admin@hospital.com", "password": "admin123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/metrics/storage", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "tables" in data
    assert "tenants" in data
    assert "overall" in data
    
    # Verify core tables are present
    table_names = [t["table_name"] for t in data["tables"]]
    assert "appointments" in table_names
    assert "patients" in table_names
    assert "doctors" in table_names
    assert "appointment_slots" in table_names
    
    # Check index and table size fields
    for t in data["tables"]:
        assert "table_size_kb" in t
        assert "index_size_kb" in t
        assert "rows" in t

def test_7_retention_comparison():
    """Verify with-retention vs without-retention trajectory generation."""
    login_res = client.post("/api/auth/login", json={"email": "admin@hospital.com", "password": "admin123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/metrics/retention?days=180", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "without_retention" in data
    assert "with_retention" in data
    assert "storage_savings_mb" in data
    assert data["storage_savings_mb"] >= 0

def test_8_baseline_and_proposed_forecasting():
    """Verify baseline and proposed forecasting algorithms compute days to exhaustion."""
    login_res = client.post("/api/auth/login", json={"email": "admin@hospital.com", "password": "admin123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/forecast", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "baseline" in data
    assert "proposed" in data
    assert "trajectory" in data
    
    proposed = data["proposed"]
    assert "confidence_score" in proposed
    assert "risk_level" in proposed
    assert "prediction_interval" in proposed
    assert proposed["confidence_score"] > 0

def test_9_failure_cases_and_security():
    """Verify failure case behavior: spike lowers confidence, cross-tenant call rejected."""
    login_res = client.post("/api/auth/login", json={"email": "admin@hospital.com", "password": "admin123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Spike test: confidence drops
    res_normal = client.get("/api/forecast?spike_multiplier=1.0", headers=headers)
    res_spiked = client.get("/api/forecast?spike_multiplier=2.5", headers=headers)
    conf_normal = res_normal.json()["proposed"]["confidence_score"]
    conf_spiked = res_spiked.json()["proposed"]["confidence_score"]
    assert conf_spiked < conf_normal

    # Cross-tenant breach test
    res_cross = client.post("/api/demo/cross-tenant-test", headers=headers)
    assert res_cross.status_code == 403
    assert "ACCESS DENIED" in res_cross.json()["detail"]

def test_10_experiment_scenarios_and_error_calculation():
    """Verify Scenarios A, B, C run and calculate actual error without hardcoding."""
    login_res = client.post("/api/auth/login", json={"email": "admin@hospital.com", "password": "admin123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post("/api/experiments/run", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data["scenarios"]) == 3
    
    for sc in data["scenarios"]:
        assert "actual_days_to_exhaustion" in sc
        assert "baseline_error_days" in sc
        assert "proposed_error_days" in sc
        assert "actual_exhaustion_date" in sc
        # Verify formula: error = abs(pred - actual)
        expected_baseline_err = abs(sc["baseline_predicted_days"] - sc["actual_days_to_exhaustion"])
        expected_proposed_err = abs(sc["proposed_predicted_days"] - sc["actual_days_to_exhaustion"])
        assert sc["baseline_error_days"] == expected_baseline_err
        assert sc["proposed_error_days"] == expected_proposed_err
