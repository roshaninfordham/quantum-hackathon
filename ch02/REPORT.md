# Challenge 02 — Formal submission

**Task:** encode star K₁,₃ and cycle C₅ as unit-disk graphs in atom
positions; design a global sweep Ω(t), δ(t) from |g…g⟩ whose measurement
returns a maximum independent set. Score: P_MIS against the deck's linear
ramp, same graph, device envelope enforced.

## Results

| Graph | Baseline (deck ramp, 4000 ns) | **Ours (GRAPE)** | Our T | Cloud (500 shots) |
|---|---|---|---|---|
| star K₁,₃ (α=3, unique MIS) | 0.727135 | **0.999998** | 1000 ns | **500/500 correct** |
| cycle C₅ (α=2, 5 MIS's) | 0.657049 | **0.999999** | 1000/2000 ns | **500/500 + 500/500 correct** |

Cloud total: **1500/1500 shots returned an optimal independent set.** The
C₅ counts split near-uniformly across all five valid answers
(114/98/97/96/95 at 1000 ns) — the machine samples the full solution
manifold, matching the designed 0.200-per-solution state (χ² consistent
with uniform).

Success condition (P_MIS strictly above baseline) exceeded by ~0.27/0.34
absolute. Both sweeps also run 2–4× faster than the baseline, which under
a Lindblad noise model (Rydberg decay + laser dephasing) widens the gap:
0.812 vs 0.380 (star), 0.926 vs 0.648 (C₅).

## Method in one paragraph

Registers are placed so blockade physics realizes exactly the target graph
(verified edge-by-edge against R_b in `score02.py`; star ρ = 5.5 µm,
pentagon s = 5.5 µm, both inside the deck's stated windows). Instead of an
adiabatic ramp, we maximize P_MIS directly with full-space adjoint-GRAPE
(16/32-dim exact, diagonal interaction tails included), warm-started from
the deck baseline, with a **projector objective** so C₅'s five degenerate
solutions are targeted as a manifold — the optimized state carries each at
exactly 0.200. Gradients are verified against finite differences at run
start; every reported number is re-scored through the judge-facing Pulser
simulator (agreement ≤ 7×10⁻⁶).

## Artifacts

- `score02.py` — scorer + selftests + deck baseline (single source of truth)
- `opt02.py` — the optimizer (all six runs: ~2 min laptop)
- `opt_*_T*.npz` — optimized knot waveforms (8 ns grid)
- `opt02_results.json`, `noise02.json` — result and noise tables
- `cloud_results_EMU_FREE.json` — measured counts + batch IDs
- `fig_ch02_results.png` — sweeps + baseline comparison
- Docs: `../docs/ch02/01-challenge.md` (plain-words explainer),
  `../docs/ch02/02-methods.md` (methods, verification incident report,
  QPU embedding analysis)
