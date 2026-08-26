# CareerLayer Deterministic Scoring Engine

`careerlayer-scoring` computes deterministic, reproducible match scores and impact deltas from structured requirement claims and integrity factors.

It has zero network dependencies, zero database dependencies, and makes zero LLM calls.

## Mathematical Formulation

$$score = 100 \times \frac{\sum_{r} w_r \times s_r \times q_r}{\sum_{r} w_r}$$

where:
- $w_r = \text{criticality}_r \times \text{necessity\_factor}_r$
- $s_r \in \{1.0 \text{ (direct)}, 0.6 \text{ (adjacent)}, 0.0 \text{ (none)}\}$
- $q_r = \text{corroboration}_r \times \text{integrity}_r$
- $\text{corroboration}_r = \min(1.0, 0.8 + 0.1 \times (\text{distinct\_spans} - 1))$
- $\text{integrity}_r \in \{0.0 \text{ (high)}, 0.5 \text{ (suspicious)}, 1.0 \text{ (clean/info)}\}$

## Credulous Score & Impact Delta

$$score\_if\_trusted = 100 \times \frac{\sum_{r} w_r \times s_r \times (q_r \text{ with integrity forced to 1.0})}{\sum_{r} w_r}$$

$$impact\_delta = score\_if\_trusted - score$$
