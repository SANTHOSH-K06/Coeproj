import datetime
import math
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from .storage_monitor import get_tenant_storage_breakdown, calculate_table_metrics
from .models import StorageConfig

def run_baseline_forecast(
    current_storage_mb: float,
    storage_limit_mb: float,
    daily_growth_mb: float,
    start_date: Optional[datetime.date] = None
) -> Dict[str, Any]:
    """
    Simple linear baseline forecasting:
    Days to Exhaustion = (Storage Limit - Current Storage) / Daily Growth
    """
    if start_date is None:
        start_date = datetime.date.today()
        
    remaining_capacity_mb = max(0.0, storage_limit_mb - current_storage_mb)
    
    if daily_growth_mb <= 0:
        days_to_exhaustion = 9999
        exhaustion_date_str = "Never"
    else:
        days_to_exhaustion = max(1, int(remaining_capacity_mb / daily_growth_mb))
        exhaustion_date = start_date + datetime.timedelta(days=days_to_exhaustion)
        exhaustion_date_str = exhaustion_date.strftime("%Y-%m-%d")
        
    return {
        "model_type": "baseline_linear",
        "current_storage_mb": round(current_storage_mb, 3),
        "storage_limit_mb": round(storage_limit_mb, 2),
        "remaining_capacity_mb": round(remaining_capacity_mb, 3),
        "average_daily_growth_mb": round(daily_growth_mb, 4),
        "days_to_exhaustion": days_to_exhaustion,
        "exhaustion_date": exhaustion_date_str
    }

def run_proposed_forecast(
    tenant_breakdown: List[Dict[str, Any]],
    table_metrics: Dict[str, Any],
    total_storage_limit_mb: float,
    retention_days: int = 365,
    sudden_spike_multiplier: float = 1.0,
    start_date: Optional[datetime.date] = None
) -> Dict[str, Any]:
    """
    Tenant-Aware Proposed Capacity Forecast.
    Incorporates:
    - Multi-tenant activity profiles (High, Medium, Low)
    - Table vs Index expansion ratio
    - Configured retention window
    - Confidence interval & volatility modeling
    """
    if start_date is None:
        start_date = datetime.date.today()
        
    total_current_mb = sum(t["total_storage_mb"] for t in tenant_breakdown)
    
    # Weighted tenant growth considering profiles
    weighted_daily_growth = 0.0
    for t in tenant_breakdown:
        base_rate = t["growth_rate_mb_day"] * sudden_spike_multiplier
        # If tenant is high growth, index pressure scales slightly higher
        if t["profile"] == "high":
            tenant_growth = base_rate * 1.08
        elif t["profile"] == "medium":
            tenant_growth = base_rate * 1.02
        else:
            tenant_growth = base_rate * 0.98
        weighted_daily_growth += tenant_growth

    # Index expansion factor: as rows grow, B-tree branch nodes add overhead
    index_ratio = table_metrics["total_index_kb"] / max(1.0, table_metrics["total_data_kb"])
    index_multiplier = 1.0 + (index_ratio * 0.15)
    adjusted_daily_growth = weighted_daily_growth * index_multiplier
    
    # Simulate forward day by day to accurately model retention leveling
    current_sim_mb = total_current_mb
    day = 0
    max_sim_days = 1500
    
    while current_sim_mb < total_storage_limit_mb and day < max_sim_days:
        day += 1
        # Retention effect: dampens growth after history exceeds retention days
        retention_damping = max(0.45, 1.0 - (day / (retention_days * 1.8)))
        daily_increment = adjusted_daily_growth * retention_damping
        current_sim_mb += daily_increment
        
    days_to_exhaustion = day
    exhaustion_date = start_date + datetime.timedelta(days=days_to_exhaustion)
    
    # Confidence calculation:
    # Stable baseline starts around 92%. Volatility (e.g. sudden spikes) drops confidence.
    base_confidence = 93.0
    if sudden_spike_multiplier > 1.5:
        confidence = max(55.0, base_confidence - ((sudden_spike_multiplier - 1.0) * 22.0))
    elif sudden_spike_multiplier > 1.0:
        confidence = max(70.0, base_confidence - ((sudden_spike_multiplier - 1.0) * 15.0))
    else:
        confidence = base_confidence
        
    # 95% Prediction Interval:
    # Error margin scales with sqrt(days_to_exhaustion) and variance
    std_error_days = max(3, int(math.sqrt(days_to_exhaustion) * (2.0 if sudden_spike_multiplier <= 1.0 else 4.0)))
    lower_bound_days = max(1, days_to_exhaustion - int(1.96 * std_error_days))
    upper_bound_days = days_to_exhaustion + int(1.96 * std_error_days)
    
    lower_bound_date = (start_date + datetime.timedelta(days=lower_bound_days)).strftime("%Y-%m-%d")
    upper_bound_date = (start_date + datetime.timedelta(days=upper_bound_days)).strftime("%Y-%m-%d")
    
    # Risk Assessment
    usage_pct = (total_current_mb / total_storage_limit_mb) * 100.0 if total_storage_limit_mb > 0 else 0
    if days_to_exhaustion < 30 or usage_pct >= 85.0:
        risk = "Critical"
    elif days_to_exhaustion < 65 or usage_pct >= 70.0 or sudden_spike_multiplier >= 2.0:
        risk = "High"
    elif days_to_exhaustion < 120 or usage_pct >= 50.0:
        risk = "Medium"
    else:
        risk = "Low"
        
    return {
        "model_type": "tenant_aware_proposed",
        "current_storage_mb": round(total_current_mb, 3),
        "storage_limit_mb": round(total_storage_limit_mb, 2),
        "adjusted_daily_growth_mb": round(adjusted_daily_growth, 4),
        "days_to_exhaustion": days_to_exhaustion,
        "exhaustion_date": exhaustion_date.strftime("%Y-%m-%d"),
        "confidence_score": round(confidence, 1),
        "risk_level": risk,
        "prediction_interval": {
            "lower_bound_date": lower_bound_date,
            "upper_bound_date": upper_bound_date,
            "margin_days": int(1.96 * std_error_days)
        },
        "retention_days_applied": retention_days,
        "spike_multiplier": sudden_spike_multiplier
    }

def generate_forecast_trajectories(
    db: Session,
    days_ahead: int = 120,
    sudden_spike_multiplier: float = 1.0
) -> Dict[str, Any]:
    """Generate side-by-side trajectory curves for Baseline vs Proposed model."""
    tenant_breakdown = get_tenant_storage_breakdown(db)
    table_metrics = calculate_table_metrics(db)
    
    # Total limit across tenants
    configs = db.query(StorageConfig).all()
    total_limit_mb = sum(c.max_storage_mb for c in configs) if configs else 75.0
    avg_retention = int(sum(c.retention_days for c in configs) / len(configs)) if configs else 365
    
    current_storage_mb = sum(t["total_storage_mb"] for t in tenant_breakdown)
    raw_daily_growth = sum(t["growth_rate_mb_day"] for t in tenant_breakdown) * sudden_spike_multiplier
    
    baseline_result = run_baseline_forecast(current_storage_mb, total_limit_mb, raw_daily_growth)
    proposed_result = run_proposed_forecast(
        tenant_breakdown, table_metrics, total_limit_mb, avg_retention, sudden_spike_multiplier
    )
    
    trajectory = []
    today = datetime.date.today()
    
    # Step every 5 days
    for day in range(0, days_ahead + 1, 5):
        point_date = (today + datetime.timedelta(days=day)).strftime("%Y-%m-%d")
        
        # Baseline: straight line
        b_val = min(total_limit_mb * 1.2, current_storage_mb + (day * raw_daily_growth))
        
        # Proposed: tenant-weighted with index overhead and retention dampening
        retention_factor = max(0.45, 1.0 - (day / (avg_retention * 1.8)))
        p_val = min(total_limit_mb * 1.2, current_storage_mb + (day * proposed_result["adjusted_daily_growth_mb"] * retention_factor))
        
        trajectory.append({
            "day": day,
            "date": point_date,
            "baseline_mb": round(b_val, 2),
            "proposed_mb": round(p_val, 2),
            "storage_limit_mb": round(total_limit_mb, 2)
        })
        
    return {
        "baseline": baseline_result,
        "proposed": proposed_result,
        "trajectory": trajectory
    }
