import random
import datetime
from typing import Dict, List, Any
from sqlalchemy.orm import Session
from .storage_monitor import get_tenant_storage_breakdown, calculate_table_metrics
from .forecasting import run_baseline_forecast, run_proposed_forecast
from .models import StorageConfig

def run_all_scenarios(db: Session, seed: int = 42) -> Dict[str, Any]:
    """
    Run 3 experimental backtesting scenarios:
    Scenario A: Stable growth
    Scenario B: Rapid tenant growth
    Scenario C: Sudden activity spike

    Calculates:
    - Actual exhaustion date (via daily state simulation)
    - Baseline prediction & Forecast Error
    - Proposed prediction & Forecast Error
    Formula: Forecast Error = ABS(predicted exhaustion date - actual exhaustion date)
    """
    random.seed(seed)
    start_date = datetime.date.today()
    
    tenant_breakdown = get_tenant_storage_breakdown(db)
    table_metrics = calculate_table_metrics(db)
    configs = db.query(StorageConfig).all()
    storage_limit_mb = sum(c.max_storage_mb for c in configs) if configs else 75.0
    avg_retention = int(sum(c.retention_days for c in configs) / len(configs)) if configs else 365
    
    current_storage_mb = sum(t["total_storage_mb"] for t in tenant_breakdown)
    base_daily_growth = sum(t["growth_rate_mb_day"] for t in tenant_breakdown)
    
    scenarios = [
        {
            "id": "scenario_a",
            "name": "Scenario A: Stable Growth",
            "description": "Consistent day-to-day appointments with minor variance (±5%) across all three tenants.",
            "spike_mult": 1.0,
            "tenant_alpha_growth_mult": 1.0,
            "spike_duration_days": 0
        },
        {
            "id": "scenario_b",
            "name": "Scenario B: Rapid Tenant Growth",
            "description": "Hospital Alpha expands clinic operations rapidly, scaling its appointment volume by 2.6x.",
            "spike_mult": 1.45,
            "tenant_alpha_growth_mult": 2.6,
            "spike_duration_days": 0
        },
        {
            "id": "scenario_c",
            "name": "Scenario C: Sudden Activity Spike",
            "description": "A seasonal surge drives a sudden 2.8x activity burst for 35 days across tenants before stabilizing.",
            "spike_mult": 2.0,
            "tenant_alpha_growth_mult": 1.5,
            "spike_duration_days": 35
        }
    ]
    
    results = []
    
    for sc in scenarios:
        # 1. Baseline Model Prediction at Day 0
        baseline_pred = run_baseline_forecast(
            current_storage_mb, 
            storage_limit_mb, 
            base_daily_growth, 
            start_date=start_date
        )
        
        # 2. Proposed Model Prediction at Day 0
        proposed_pred = run_proposed_forecast(
            tenant_breakdown, 
            table_metrics, 
            storage_limit_mb, 
            retention_days=avg_retention,
            sudden_spike_multiplier=sc["spike_mult"],
            start_date=start_date
        )
        
        # 3. Simulate Actual Ground Truth Day-by-Day Progression
        sim_storage = current_storage_mb
        actual_day = 0
        max_sim_days = 2000
        
        while sim_storage < storage_limit_mb and actual_day < max_sim_days:
            actual_day += 1
            
            # Scenario-specific daily growth physics
            if sc["spike_duration_days"] > 0:
                if actual_day <= sc["spike_duration_days"]:
                    day_mult = 2.8 * random.uniform(0.92, 1.08)
                else:
                    day_mult = 1.15 * random.uniform(0.95, 1.05)
            elif sc["id"] == "scenario_b":
                # Alpha ramps up continuously
                day_mult = (1.0 + (min(actual_day, 60) / 60.0) * (sc["tenant_alpha_growth_mult"] - 1.0)) * random.uniform(0.95, 1.05)
            else:
                day_mult = 1.0 * random.uniform(0.96, 1.04)
                
            # Retention dampening in ground truth
            retention_effect = max(0.48, 1.0 - (actual_day / (avg_retention * 1.75)))
            daily_addition = base_daily_growth * day_mult * 1.12 * retention_effect
            sim_storage += daily_addition
            
        actual_exhaustion_date = start_date + datetime.timedelta(days=actual_day)
        
        # Forecast Error = ABS(predicted exhaustion date - actual exhaustion date)
        baseline_pred_days = baseline_pred["days_to_exhaustion"]
        proposed_pred_days = proposed_pred["days_to_exhaustion"]
        
        baseline_error_days = abs(baseline_pred_days - actual_day)
        proposed_error_days = abs(proposed_pred_days - actual_day)
        
        error_reduction_pct = round(
            ((baseline_error_days - proposed_error_days) / max(1, baseline_error_days)) * 100.0, 1
        ) if baseline_error_days > 0 else 0.0
        
        results.append({
            "scenario_id": sc["id"],
            "name": sc["name"],
            "description": sc["description"],
            "actual_days_to_exhaustion": actual_day,
            "actual_exhaustion_date": actual_exhaustion_date.strftime("%Y-%m-%d"),
            "baseline_predicted_days": baseline_pred_days,
            "baseline_predicted_date": baseline_pred["exhaustion_date"],
            "proposed_predicted_days": proposed_pred_days,
            "proposed_predicted_date": proposed_pred["exhaustion_date"],
            "baseline_error_days": baseline_error_days,
            "proposed_error_days": proposed_error_days,
            "error_reduction_percent": error_reduction_pct,
            "proposed_confidence": proposed_pred["confidence_score"],
            "proposed_risk": proposed_pred["risk_level"]
        })
        
    avg_baseline_error = round(sum(r["baseline_error_days"] for r in results) / len(results), 1)
    avg_proposed_error = round(sum(r["proposed_error_days"] for r in results) / len(results), 1)
    overall_reduction = round(((avg_baseline_error - avg_proposed_error) / avg_baseline_error) * 100.0, 1)
    
    return {
        "execution_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "storage_limit_mb": storage_limit_mb,
        "scenarios": results,
        "summary": {
            "average_baseline_error_days": avg_baseline_error,
            "average_proposed_error_days": avg_proposed_error,
            "overall_accuracy_improvement_pct": overall_reduction
        }
    }
