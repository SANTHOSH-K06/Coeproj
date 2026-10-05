"""Persistent storage measurements and snapshot-based forecasting."""

from __future__ import annotations

import datetime
import math
from typing import Any

from sqlalchemy.orm import Session

from .models import StorageSnapshot
from .storage_monitor import calculate_table_metrics, get_tenant_storage_breakdown


def capture_storage_snapshot(db: Session, captured_at: datetime.datetime | None = None) -> list[StorageSnapshot]:
    """Persist one cluster snapshot and one scoped snapshot per tenant."""
    captured_at = captured_at or datetime.datetime.now(datetime.timezone.utc)
    table_metrics = calculate_table_metrics(db)
    tenants = get_tenant_storage_breakdown(db)
    total_storage = sum(tenant["total_storage_mb"] for tenant in tenants)
    total_limit = sum(tenant["storage_limit_mb"] for tenant in tenants)
    rows = [
        StorageSnapshot(
            tenant_id=None,
            captured_at=captured_at,
            storage_mb=round(total_storage, 3),
            storage_limit_mb=round(total_limit, 2),
            usage_percent=round((total_storage / total_limit * 100.0) if total_limit else 0.0, 2),
            physical_db_size_kb=round(table_metrics["physical_db_size_kb"], 2),
            table_metrics=table_metrics["tables"],
        )
    ]
    rows.extend(
        StorageSnapshot(
            tenant_id=tenant["tenant_id"],
            captured_at=captured_at,
            storage_mb=tenant["total_storage_mb"],
            storage_limit_mb=tenant["storage_limit_mb"],
            usage_percent=tenant["usage_percent"],
            physical_db_size_kb=0.0,
            table_metrics=None,
        )
        for tenant in tenants
    )
    db.add_all(rows)
    db.commit()
    for row in rows:
        db.refresh(row)
    return rows


def _solve_linear_system(matrix: list[list[float]], values: list[float]) -> list[float] | None:
    """Solve a small dense system using Gaussian elimination with pivoting."""
    size = len(values)
    augmented = [matrix[row][:] + [values[row]] for row in range(size)]
    for col in range(size):
        pivot = max(range(col, size), key=lambda row: abs(augmented[row][col]))
        if abs(augmented[pivot][col]) < 1e-12:
            return None
        augmented[col], augmented[pivot] = augmented[pivot], augmented[col]
        divisor = augmented[col][col]
        augmented[col] = [entry / divisor for entry in augmented[col]]
        for row in range(size):
            if row == col:
                continue
            factor = augmented[row][col]
            augmented[row] = [
                augmented[row][entry] - factor * augmented[col][entry]
                for entry in range(size + 1)
            ]
    return [augmented[row][-1] for row in range(size)]


def polynomial_storage_forecast(
    db: Session,
    storage_limit_mb: float,
    horizon_days: int = 365,
) -> dict[str, Any]:
    """Fit a quadratic to daily aggregate snapshots and project a monotone capacity curve."""
    snapshots = (
        db.query(StorageSnapshot)
        .filter(StorageSnapshot.tenant_id.is_(None))
        .order_by(StorageSnapshot.captured_at.asc())
        .all()
    )
    # Consolidate hourly samples to one mean value per day, preventing busy capture
    # schedules from giving a single calendar day disproportionate influence.
    by_day: dict[datetime.date, list[float]] = {}
    for snapshot in snapshots:
        by_day.setdefault(snapshot.captured_at.date(), []).append(snapshot.storage_mb)
    daily = sorted((day, sum(values) / len(values)) for day, values in by_day.items())
    if len(daily) < 3:
        return {
            "model_type": "quadratic_snapshot_trend",
            "status": "insufficient_history",
            "required_snapshots": 3,
            "available_snapshots": len(snapshots),
            "distinct_days": len(daily),
            "trajectory": [],
            "days_to_exhaustion": None,
            "exhaustion_date": None,
        }

    origin = daily[-1][0]
    points = [((day - origin).days, value) for day, value in daily[-90:]]
    # Fit y = a*x^2 + b*x + c using the normal equations.
    powers = [sum(x ** power for x, _ in points) for power in range(5)]
    weighted = [sum((x ** power) * y for x, y in points) for power in range(3)]
    coefficients = _solve_linear_system(
        [[powers[row + col] for col in range(3)] for row in range(3)], weighted
    )
    if coefficients is None:
        return {
            "model_type": "quadratic_snapshot_trend",
            "status": "degenerate_history",
            "required_snapshots": 3,
            "available_snapshots": len(snapshots),
            "trajectory": [],
            "days_to_exhaustion": None,
            "exhaustion_date": None,
        }

    quadratic, linear, intercept = coefficients
    current = daily[-1][1]
    trajectory = [{"day": 0, "storage_mb": round(current, 3)}]
    exhaustion_day = 0 if current >= storage_limit_mb else None
    projected = current
    for day in range(1, horizon_days + 1):
        fit_value = quadratic * day * day + linear * day + intercept
        # Forecasts must not imply that used storage is freed by a curve-fit artifact.
        projected = max(projected, fit_value)
        trajectory.append({"day": day, "storage_mb": round(projected, 3)})
        if exhaustion_day is None and projected >= storage_limit_mb:
            exhaustion_day = day

    return {
        "model_type": "quadratic_snapshot_trend",
        "status": "ok",
        "available_snapshots": len(snapshots),
        "distinct_days": len(daily),
        "fit_points": len(points),
        "coefficients": {
            "quadratic": round(quadratic, 8),
            "linear": round(linear, 8),
            "intercept": round(intercept, 6),
        },
        "current_storage_mb": round(current, 3),
        "storage_limit_mb": round(storage_limit_mb, 2),
        "days_to_exhaustion": exhaustion_day,
        "exhaustion_date": (
            (origin + datetime.timedelta(days=exhaustion_day)).isoformat()
            if exhaustion_day is not None else None
        ),
        "trajectory": trajectory,
    }
