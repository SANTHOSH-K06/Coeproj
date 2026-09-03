import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, 
    UniqueConstraint, Index, Boolean, Text
)
from sqlalchemy.orm import relationship
from .database import Base

def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    growth_rate_profile = Column(String(50), default="medium")  # high, medium, low
    created_at = Column(DateTime, default=utc_now)

    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    doctors = relationship("Doctor", back_populates="tenant", cascade="all, delete-orphan")
    patients = relationship("Patient", back_populates="tenant", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="tenant", cascade="all, delete-orphan")
    slots = relationship("AppointmentSlot", back_populates="tenant", cascade="all, delete-orphan")
    storage_config = relationship("StorageConfig", back_populates="tenant", uselist=False, cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="tenant", cascade="all, delete-orphan")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(200), nullable=False)
    role = Column(String(50), nullable=False, default="staff")  # admin, staff
    created_at = Column(DateTime, default=utc_now)

    tenant = relationship("Tenant", back_populates="users")

class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    specialty = Column(String(100), nullable=False)
    room_number = Column(String(50), nullable=True)

    tenant = relationship("Tenant", back_populates="doctors")
    appointments = relationship("Appointment", back_populates="doctor")
    slots = relationship("AppointmentSlot", back_populates="doctor")

    __table_args__ = (
        Index("ix_doctor_tenant_name", "tenant_id", "name"),
    )

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    medical_record_num = Column(String(50), nullable=False)
    phone = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    tenant = relationship("Tenant", back_populates="patients")
    appointments = relationship("Appointment", back_populates="patient")

    __table_args__ = (
        Index("ix_patient_tenant_mrn", "tenant_id", "medical_record_num"),
    )

class AppointmentSlot(Base):
    __tablename__ = "appointment_slots"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(String(20), nullable=False, index=True)  # YYYY-MM-DD
    slot_time = Column(String(20), nullable=False)         # HH:MM AM/PM
    is_available = Column(Boolean, default=True)

    tenant = relationship("Tenant", back_populates="slots")
    doctor = relationship("Doctor", back_populates="slots")

    __table_args__ = (
        UniqueConstraint("tenant_id", "doctor_id", "date", "slot_time", name="uq_slot_tenant_doctor_date_time"),
    )

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(String(20), nullable=False, index=True)  # YYYY-MM-DD
    slot_time = Column(String(20), nullable=False)         # HH:MM AM/PM e.g. 10:00 AM
    reason = Column(String(255), default="General Consultation")
    status = Column(String(50), default="CONFIRMED")       # CONFIRMED, COMPLETED, CANCELLED
    created_at = Column(DateTime, default=utc_now)

    tenant = relationship("Tenant", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")
    patient = relationship("Patient", back_populates="appointments")

    # DATABASE-LEVEL DOUBLE-BOOKING PREVENTION CONSTRAINT:
    __table_args__ = (
        UniqueConstraint("tenant_id", "doctor_id", "date", "slot_time", name="uq_appointment_doctor_slot"),
        Index("ix_appointment_tenant_date", "tenant_id", "date"),
    )

class StorageConfig(Base):
    __tablename__ = "storage_configs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    max_storage_mb = Column(Float, default=25.0)       # Configurable storage limit (MB)
    retention_days = Column(Integer, default=365)     # Configurable retention (default 365 days)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    tenant = relationship("Tenant", back_populates="storage_config")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    user_email = Column(String(255), nullable=True)
    action = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)       # SUCCESS, REJECTED, ACCESS DENIED
    details = Column(Text, nullable=True)
    ip_address = Column(String(50), default="127.0.0.1")
    created_at = Column(DateTime, default=utc_now)

    tenant = relationship("Tenant", back_populates="audit_logs")
