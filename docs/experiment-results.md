# Experiment Results Summary

## Current benchmark summary
The current project reports the following performance pattern for its simulated scenarios:

- Scenario A: Stable growth
- Scenario B: Rapid tenant growth
- Scenario C: Sudden activity spike

The experiment engine compares actual exhaustion dates against baseline and proposed predictions and calculates the absolute error. The design intentionally keeps the comparison explicit so both the improvement and the failure mode remain visible.

## Interpretation
The proposed tenant-aware model is expected to outperform the simple baseline in growth-heavy or retention-sensitive scenarios, while the baseline may still be competitive when the system is stable and the data signal is weak.

## Operational takeaway
The project does not hide the uncertainty. It shows both forecast quality and model limitations, which is essential for a healthcare capacity planning tool.
