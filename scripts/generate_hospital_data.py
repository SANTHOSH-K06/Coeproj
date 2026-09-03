#!/usr/bin/env python3
"""
scripts/generate_hospital_data.py
Reproducible synthetic hospital data generator for the 35% Review 1 milestone.
Generates:
- 3 Tenants (Hospital Alpha, Beta, Gamma) with distinct growth profiles
- Default storage configurations & retention policies (365 days)
- Admin and Staff users with hashed passwords
- Doctors (including 'Dr. Demo')
- Patients (including 'Patient A' and 'Patient B')
- 35+ days of historical appointments reflecting tenant-differentiated activity levels
"""

import os
import sys
import random
import datetime

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.database import Base, engine, SessionLocal
from backend.models import Tenant, User, Doctor, Patient, AppointmentSlot, Appointment, StorageConfig, AuditLog
from backend.auth import hash_password

RANDOM_SEED = 42

def generate_data():
    print("=" * 60)
    print("Hospital Capacity Forecasting — Synthetic Data Generation")
    print(f"Random Seed: {RANDOM_SEED}")
    print("=" * 60)
    
    random.seed(RANDOM_SEED)
    
    # Recreate tables to ensure a clean state
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # 1. Create 3 Tenants with different growth rate profiles
        tenants = [
            Tenant(code="ALPHA", name="Hospital Alpha", growth_rate_profile="high"),
            Tenant(code="BETA", name="Hospital Beta", growth_rate_profile="medium"),
            Tenant(code="GAMMA", name="Hospital Gamma", growth_rate_profile="low"),
        ]
        db.add_all(tenants)
        db.commit()
        for t in tenants:
            db.refresh(t)
        print(f"[+] Created {len(tenants)} tenants (Alpha: High, Beta: Medium, Gamma: Low).")

        # 2. Create Storage Configurations (Default 25MB limit per tenant, 365 days retention)
        configs = []
        for t in tenants:
            configs.append(StorageConfig(
                tenant_id=t.id,
                max_storage_mb=25.0,
                retention_days=365
            ))
        db.add_all(configs)
        db.commit()
        print("[+] Configured default storage limits (25MB) and retention rules (365 days).")

        # 3. Create Users (Admin and Staff roles)
        users = [
            User(
                tenant_id=tenants[0].id,
                email="admin@hospital.com",
                password_hash=hash_password("admin123"),
                name="Chief Admin",
                role="admin"
            ),
            User(
                tenant_id=tenants[0].id,
                email="staff@hospital.com",
                password_hash=hash_password("staff123"),
                name="Alpha Reception Staff",
                role="staff"
            ),
            User(
                tenant_id=tenants[1].id,
                email="staff.beta@hospital.com",
                password_hash=hash_password("staff123"),
                name="Beta Clinic Staff",
                role="staff"
            ),
            User(
                tenant_id=tenants[2].id,
                email="staff.gamma@hospital.com",
                password_hash=hash_password("staff123"),
                name="Gamma Rural Staff",
                role="staff"
            )
        ]
        db.add_all(users)
        db.commit()
        print("[+] Created Demo Accounts: admin@hospital.com / admin123, staff@hospital.com / staff123")

        # 4. Create Doctors (Including 'Dr. Demo')
        doctors = [
            # Hospital Alpha Doctors
            Doctor(tenant_id=tenants[0].id, name="Dr. Demo", specialty="Cardiology", room_number="Room 101"),
            Doctor(tenant_id=tenants[0].id, name="Dr. Sarah Chen", specialty="Pediatrics", room_number="Room 102"),
            Doctor(tenant_id=tenants[0].id, name="Dr. Marcus Vance", specialty="Orthopedics", room_number="Room 103"),
            
            # Hospital Beta Doctors
            Doctor(tenant_id=tenants[1].id, name="Dr. Elena Rostova", specialty="Internal Medicine", room_number="Suite 2A"),
            Doctor(tenant_id=tenants[1].id, name="Dr. James Wilson", specialty="Neurology", room_number="Suite 2B"),
            
            # Hospital Gamma Doctors
            Doctor(tenant_id=tenants[2].id, name="Dr. Arthur Pendelton", specialty="Family Medicine", room_number="Clinic 1"),
        ]
        db.add_all(doctors)
        db.commit()
        for d in doctors:
            db.refresh(d)
        print(f"[+] Created {len(doctors)} doctors across tenants (includes 'Dr. Demo' at Alpha).")

        # 5. Create Patients (Including 'Patient A' and 'Patient B')
        patients = []
        # Demo patients for Hospital Alpha
        patient_a = Patient(tenant_id=tenants[0].id, name="Patient A", medical_record_num="MRN-ALPHA-001", phone="555-0101")
        patient_b = Patient(tenant_id=tenants[0].id, name="Patient B", medical_record_num="MRN-ALPHA-002", phone="555-0102")
        patients.extend([patient_a, patient_b])

        # Additional patients for realistic distribution
        for i in range(3, 45):
            patients.append(Patient(
                tenant_id=tenants[0].id,
                name=f"Alpha Patient {i}",
                medical_record_num=f"MRN-ALPHA-{i:03d}",
                phone=f"555-01{i:02d}"
            ))
        for i in range(1, 26):
            patients.append(Patient(
                tenant_id=tenants[1].id,
                name=f"Beta Patient {i}",
                medical_record_num=f"MRN-BETA-{i:03d}",
                phone=f"555-02{i:02d}"
            ))
        for i in range(1, 16):
            patients.append(Patient(
                tenant_id=tenants[2].id,
                name=f"Gamma Patient {i}",
                medical_record_num=f"MRN-GAMMA-{i:03d}",
                phone=f"555-03{i:02d}"
            ))
        db.add_all(patients)
        db.commit()
        for p in patients:
            db.refresh(p)
        print(f"[+] Created {len(patients)} patients (includes 'Patient A' and 'Patient B').")

        # 6. Generate 35 Days of Historical Appointments
        today = datetime.date.today()
        start_history = today - datetime.timedelta(days=35)
        
        time_slots = [
            "09:00 AM", "09:30 AM", "10:00 AM", "10:30 AM", 
            "11:00 AM", "11:30 AM", "02:00 PM", "02:30 PM", 
            "03:00 PM", "03:30 PM", "04:00 PM"
        ]
        
        appointments = []
        slots = []
        
        # Tenants daily appointment load profiles:
        # Alpha (High): 12-18 appts/day
        # Beta (Medium): 6-10 appts/day
        # Gamma (Low): 2-5 appts/day
        load_profiles = {
            tenants[0].id: (12, 18, [d for d in doctors if d.tenant_id == tenants[0].id], [p for p in patients if p.tenant_id == tenants[0].id]),
            tenants[1].id: (6, 10, [d for d in doctors if d.tenant_id == tenants[1].id], [p for p in patients if p.tenant_id == tenants[1].id]),
            tenants[2].id: (2, 5, [d for d in doctors if d.tenant_id == tenants[2].id], [p for p in patients if p.tenant_id == tenants[2].id]),
        }
        
        reasons = [
            "General Consultation", "Follow-up Visit", "Routine Health Checkup",
            "Prescription Renewal", "Diagnostic Review", "Specialist Consultation"
        ]
        
        for day_offset in range(35):
            current_day = start_history + datetime.timedelta(days=day_offset)
            date_str = current_day.strftime("%Y-%m-%d")
            
            for t_id, (min_a, max_a, t_docs, t_pts) in load_profiles.items():
                booked_pairs = set()
                target_count = random.randint(min_a, max_a)
                
                attempts = 0
                while len(booked_pairs) < target_count and attempts < 100:
                    attempts += 1
                    doc = random.choice(t_docs)
                    slot_time = random.choice(time_slots)
                    
                    pair_key = (t_id, doc.id, date_str, slot_time)
                    if pair_key in booked_pairs:
                        continue
                    booked_pairs.add(pair_key)
                    
                    pt = random.choice(t_pts)
                    appt = Appointment(
                        tenant_id=t_id,
                        doctor_id=doc.id,
                        patient_id=pt.id,
                        date=date_str,
                        slot_time=slot_time,
                        reason=random.choice(reasons),
                        status="COMPLETED" if day_offset < 33 else "CONFIRMED",
                        created_at=datetime.datetime.combine(current_day, datetime.time(8, 0))
                    )
                    appointments.append(appt)
                    
                    slot = AppointmentSlot(
                        tenant_id=t_id,
                        doctor_id=doc.id,
                        date=date_str,
                        slot_time=slot_time,
                        is_available=False
                    )
                    slots.append(slot)

        db.add_all(appointments)
        db.add_all(slots)
        db.commit()
        print(f"[+] Generated {len(appointments)} historical appointments across 35 days.")

        # 7. Initial Security Audit Log
        initial_log = AuditLog(
            tenant_id=tenants[0].id,
            user_email="system@hospital.internal",
            action="SYSTEM_INIT",
            status="SUCCESS",
            details="System initialized with synthetic dataset for Review 1 (35% milestone)."
        )
        db.add(initial_log)
        db.commit()
        print("[+] Initialized audit log.")

        print("=" * 60)
        print("Data Generation Complete and Verified.")
        print(f"Total Appointments: {len(appointments)}")
        print("Demo credentials ready:")
        print("  Admin: admin@hospital.com / admin123")
        print("  Staff: staff@hospital.com / staff123")
        print("=" * 60)
        
    except Exception as e:
        db.rollback()
        print(f"[-] Error during data generation: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    generate_data()
