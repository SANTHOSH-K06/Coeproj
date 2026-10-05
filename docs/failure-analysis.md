# Failure Analysis

The forecasting model is not presented as perfect. In practice, forecast quality depends on historical signal quality, sudden growth changes, retention policy changes, and the presence of heavy index expansion.

## Failure modes considered

- low historical data
- sudden capacity spike
- tenant churn or rapid scale-out
- retention policy change
- index-heavy growth pattern
- limited training signal across tenant profiles

## Interpretation

The model performs best when growth patterns are consistent and retention effects are stable. It may underperform when a tenant suddenly changes behavior or when an index expands faster than the rows themselves. This is why the project reports scenario-specific error and explicitly compares baseline and proposed models.

## Operational recommendation

Forecast confidence should be used as an operational signal, not a guarantee. The project is designed to show risk, confidence, and uncertainty so administrators can decide whether to act or simply monitor a pattern.
