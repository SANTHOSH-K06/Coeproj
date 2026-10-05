# Forecasting Model

## Baseline model
The baseline forecast estimates the remaining time before exhaustion by dividing the remaining capacity by the average daily growth rate.

- Formula: `(storage_limit - current_storage) / average_daily_growth`
- Result: a simple but sensitive model that does not account for tenant profile, retention policy, or index-growth pressure.

## Proposed model
The proposed forecast refines this by:

- weighting the growth profile for each tenant,
- adjusting for index overhead and B-tree expansion,
- applying retention-dampening effects,
- using volatility and confidence estimation for risk scoring,
- generating a lower and upper prediction interval.

The platform exposes results through the forecast API and dashboard, allowing a direct comparison between baseline and proposed outputs.

## Metrics exposed

- current storage
- storage limit
- daily growth
- days to exhaustion
- exhaustion date
- confidence score
- risk level
- prediction interval

## Why this matters
Hospital capacity planning is safer when it is proactive. The forecast engine provides early warning to administrators before capacity becomes critical, reducing late action and service disruption risk.
