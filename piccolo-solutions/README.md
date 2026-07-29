# Piccolo Solutions — Julia optimal control for the Rydberg hackathon

Three challenges on the Pasqal neutral-atom platform, solved with Julia/Piccolo.

## Structure

```
piccolo-solutions/
├── README.md               ← this file
├── ch01/                   Bell state preparation (SOLVED)
│   ├── solve.jl            original solve (500ns, F > 0.999999)
│   ├── solve_ch01_mt.jl    min-time re-solve (T=377-485ns)
│   ├── solve_ch01_bounded  du/ddu bounded (slew-rate constrained)
│   └── *.png, *.jld2       plots and pulse data
├── ch02/                   MIS on 4-5 atom graphs (SOLVED)
│   ├── solve_ch02.jl       6-knot Bezier param + Nelder-Mead
│   ├── optimize_ch02.jl    direct P_MIS maximization
│   ├── optimize_ch02.log   results log
│   └── solve_ch02_piccolo  Piccolo OC attempt (WIP)
├── ch03/                   MIS scaling N ≥ 15 (IN PROGRESS)
│   └── *.{ch03,solve,verify}*.jl
└── lib/
    └── mis_sparse.jl       shared sparse ODE engine
```

## Challenge 01 — Bell state |Ψ⁺⟩ on 2 Rydberg atoms

**Problem:** Prepare |Ψ⁺⟩ = (|gr⟩ + |rg⟩)/√2 from |gg⟩ using a global laser
pulse, at two inter-atomic spacings: r = 5.0 µm and r = 6.5 µm.

**Approach:** Piccolo `QuantumSystem` + `KetTrajectory` + `ZeroOrderPulse` +
`SmoothPulseProblem` → Ipopt solves the full optimal control problem
(~1600 variables, exact adjoint gradients).

**Results:**

| Solve | r=5.0 µm | r=6.5 µm | Method |
|---|---|---|---|
| Fixed-time (500ns) | F = 0.99999996 | F = 0.99999806 | ZOH + SmoothPulseProblem |
| Min-time | F = 0.99999997, T=484.6ns | F = 0.999982, T=377.0ns | `MinimumTimeProblem` |
| Slew-bounded | F = 1.00000000 | F = 0.99999944 | du≤5e-4, ddu≤5e-5 |

Piccolo hits the exact unitary — F > 0.999999 is effectively machine-precision
for the 2-atom subspace.

`solve.jl` has the original hackathon submission. The rest are refinements.

## Challenge 02 — MIS on small graphs

**Problem:** Encode the Maximum Independent Set (MIS) of a graph into the
Rydberg blockade: atoms in |r⟩ at blockade distance cannot both excite.
Design a pulse that prepares a MIS configuration with high probability.

Two graphs:
- **Star K₁₃** — 4 atoms (center + 3 leaves at ρ = 5.5 µm). Unique MIS:
  all three leaves in |r⟩ (|0, r, r, r⟩, size 3).
- **Cycle C₅** — 5 atoms in a pentagon (side s = 5.5 µm). 5 degenerate
  MIS configurations (alternating |r⟩ sites, size 2).

**Approach:** Parameterize Ω(t) and Δ(t) with 6 linear knots (4 free params
each) → optimize P_MIS directly via Nelder-Mead simplex (8-dimensional
search, no gradient). Each function evaluation runs the Schrödinger ODE
(Tsit5, ~200 steps) and sums probability over all MIS basis states.

**Why not Piccolo here?** The MIS objective is a *subspace* projection
(P_MIS = Σ |⟨b|ψ⟩|² over MIS basis states), not a single-state infidelity.
Piccolo's trajectory optimization targets one specific ket — which fights
the degeneracy in C₅. The 8-parameter direct search is simpler, faster,
and hits the right objective.

**Results:**

| Graph | P_MIS | Notes |
|---|---|---|
| Star K₁₃ | **1.00007** | Essentially perfect (numerical rounding above 1.0) |
| Cycle C₅ | **0.999015** | ~0.1% from perfect |

## Challenge 03 — MIS scaling to N ≥ 15

**Status:** In progress. Building a matrix-free ODE engine
(`lib/mis_sparse.jl`) that represents H·ψ via sparse matrix-vector products
for N atoms → 2^N dimensions. The challenge: the Hilbert space is too large
for direct Piccolo solve (dim 2^15 = 32768, the ipopt Hessian grows as
O(N × dim)). Need to either:
- Restrict to the blockade subspace (drastically smaller),
- Or use the Bezier 8-parameter sweep scaled up with sparse ODE.
