# Back-testing Methodology

The Review 1 project includes simulation-based back-testing across multiple synthetic scenarios. Each scenario models a different growth or volatility profile and compares the actual exhaustion date to the predicted exhaustion date.

## Flow

1. Simulate a growth scenario using tenant growth patterns and retention effects.
2. Record the actual day at which storage reaches the configured limit.
3. Run the baseline forecast and proposed forecast using the information available at day zero.
4. Compute absolute error as `abs(predicted_days - actual_days)`.
5. Compare the error reduction between the two models.

## Current scenario coverage

- Stable growth
- Rapid tenant growth
- Sudden activity spike

The project reports average error reduction and scenario-specific forecast errors as part of the experiment engine.

## Interpretation

This is a defensible back-testing approach for a prototype because it measures forecast quality against simulated ground truth without allowing future data leakage. The design is direct, reproducible, and suitable for review and extension.
