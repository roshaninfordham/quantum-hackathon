# Piccolo Solutions — Julia optimal control

Julia/Piccolo optimal control approach to the hackathon challenges, using Ipopt
(interior-point NLP solver) with exact adjoint gradients via DirectTrajOpt.

## Structure

| Folder | Contents | Status |
|---|---|---|
| `ch01/` | Bell state (|Ψ⁺⟩) on 2 Rydberg atoms | **Solved** F > 0.999999 |
| `ch02/` | MIS via pulse shaping on 4–5 atom graphs | In progress |

## Ch01 — Bell state

ZeroOrderPulse + SmoothPulseProblem + MinimumTimeProblem, both spacings:

| Spacing | Fixed-time (T=500ns) | Min-time |
|---|---|---|
| r=5.0 µm (strong blockade, V/Ω≈8.8) | F = 0.99999996 | F = 0.99999997, T=484.6ns |
| r=6.5 µm (weak blockade, V/Ω≈1.8) | F = 0.99999806 | F = 0.99998205, T=377.0ns |

Slope- and acceleration-bounded re-solve (`du_bound=5e-4`, `ddu_bound=5e-5`) pending.

## Ch02 — MIS optimization

Bezier-parameterized Nelder-Mead optimization (complete) → Piccolo optimal control (in progress):

| Graph | N | Bezier P_MIS | Piccolo OC |
|---|---|---|---|
| Star K₁₃ | 4 | 1.00007 | — |
| Cycle C₅ | 5 | 0.999015 | — |
