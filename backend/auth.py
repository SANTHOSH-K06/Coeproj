import os
import hashlib
import hmac
import datetime
from typing import Optional
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .database import get_db
from .models import User, AuditLog

SECRET_KEY = os.getenv("JWT_SECRET", "super-secret-hospital-capacity-forecast-key-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

security = HTTPBearer()

def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256 with random salt."""
    salt = os.urandom(16).hex()
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"{salt}:{key.hex()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against the stored salt:hash."""
    try:
        salt, stored_hash = hashed_password.split(":")
        key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), 100000)
        return hmac.compare_digest(key.hex(), stored_hash)
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.now(datetime.timezone.utc) + expires_delta
    else:
        expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

def require_admin(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
    if current_user.role != "admin":
        # Log unauthorized attempt
        log = AuditLog(
            tenant_id=current_user.tenant_id,
            user_email=current_user.email,
            action="UNAUTHORIZED_CONFIG_ATTEMPT",
            status="ACCESS DENIED",
            details=f"User {current_user.email} with role '{current_user.role}' attempted admin-only configuration."
        )
        db.add(log)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Admin privileges required to modify storage, retention, or forecasting configuration."
        )
    return current_user

def verify_tenant_access(user: User, tenant_id: int, db: Session) -> bool:
    """Ensure user only accesses their tenant unless they are global admin."""
    if user.role == "admin" and (user.tenant_id is None or user.tenant_id == tenant_id):
        return True
    if user.tenant_id == tenant_id:
        return True
        
    # Cross-tenant violation!
    log = AuditLog(
        tenant_id=tenant_id,
        user_email=user.email,
        action="CROSS_TENANT_ACCESS_ATTEMPT",
        status="ACCESS DENIED",
        details=f"User {user.email} (Tenant {user.tenant_id}) attempted unauthorized access to Tenant {tenant_id}."
    )
    db.add(log)
    db.commit()
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="ACCESS DENIED: Cross-tenant data access violation."
    )
