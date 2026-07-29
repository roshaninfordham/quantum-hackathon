# Challenge 02 — Methods, results, and the verification story

Companion code: [`ch02/score02.py`](../../ch02/score02.py) (scorer) and
[`ch02/opt02.py`](../../ch02/opt02.py) (optimizer). Same discipline as
Challenge 01: one scorer, device limits read at call time, conventions
selftested, every number cross-validated.

## 1. The scorer and its selftests

P_MIS = Σ |⟨b|ψ(T)⟩|² over bitstrings b that are independent sets of size
exactly α(G), computed from the exact state vector (16/32-dim — no
sampling noise in the design loop; shot noise only enters at cloud
validation).

Selftests run every session:
- idle pulse keeps |g…g⟩ (catches basis-ordering mistakes — and did:
  pulser's per-qubit basis is (r, g), so |g…g⟩ is the *last* index; the
  first run of the selftest failed and forced the fix)
- both registers verified edge-by-edge against R_b (`check_unit_disk`)
- MIS enumeration: star has exactly 1 solution, C₅ exactly 5

**Deck baselines (T = 4000 ns ramp, exact):** star **0.727135**,
cycle **0.657049**. The C₅ baseline distributes exactly 0.1314 to each of
the five solutions — the global drive cannot break the pentagon's symmetry,
a free physics check on the whole pipeline.

## 2. The optimizer

The ch01 adjoint-GRAPE engine, generalized:
- **Full Hilbert space** (2⁴/2⁵) — exact diagonal interaction tails
  included (the pentagon's non-adjacent pairs still repel at
  U_diag = 1.74 rad/µs; ignoring that would be a silent model error).
- **Projector objective**: maximize ⟨ψ|P_MIS|ψ⟩. For C₅ the target is a
  5-dimensional degenerate manifold — a single-state objective would
  arbitrarily pick one solution and fight the symmetry.
- 8 ns knots (2× device clock, exactly representable), Ω pinned to zero at
  both ends, device bounds as box constraints, light smoothness penalty.
- **Warm start from the baseline ramp** — the optimizer starts in the
  adiabatic basin and improves it, rather than searching from noise.
- Gradient verified against finite differences at run start
  (4.4×10⁻⁵ relative); the run aborts if that check fails.

Compute: all six (graph × duration) optimizations in ~2 minutes on a laptop.

## 3. Results

| Graph | T (ns) | internal model | **Pulser (judge's sim)** |
|---|---|---|---|
| star K₁,₃ | 1000 | 0.999998 | **0.999998** |
| star K₁,₃ | 2000 | 0.999983 | 0.999986 |
| star K₁,₃ | 4000 | 0.999986 | 0.999991 |
| cycle C₅ | 1000 | 0.999997 | 0.999993 |
| cycle C₅ | 2000 | 0.999998 | **0.999999** |
| cycle C₅ | 4000 | 1.000000 | 0.999997 |

Internal ↔ Pulser agreement ≤ 7×10⁻⁶ at every point. C₅'s five answers
each receive exactly 0.200 — the sweep prepares a coherent superposition
over the *entire* solution manifold.

Under the ch01 noise model (Rydberg decay τ = 100 µs, dephasing 0.22 µs⁻¹):

| Graph | baseline (4000 ns) | GRAPE (1000 ns) |
|---|---|---|
| star K₁,₃ | 0.380 | **0.812** |
| cycle C₅ | 0.648 | **0.926** |

The 4× shorter duration converts the noiseless tie into a hardware
blowout — the same "duration is the noise coupling" law measured in
[ch01 docs 07](../ch01/07-hardware.md).

## 4. Verification incident report (why the discipline matters)

Our teammate's independent track (`piccolo-solutions/ch02/`) optimized
spline sweeps against a hand-rolled ODE simulator and logged
star P_MIS = **1.000067** — a value > 1, which is unphysical and flags an
integrator-tolerance artifact. Re-scoring their logged knots in the
judge-facing Pulser scorer gives:

| Graph | their log | Pulser verdict | deck baseline |
|---|---|---|---|
| star K₁,₃ | 1.000067 | **0.545** — *below* baseline | 0.727 |
| cycle C₅ | 0.999015 | 0.852 — above baseline | 0.657 |

The lesson is not "their optimizer is worse" — it's that **an optimizer
must talk to the simulator you'll be judged by** (prompt-pack rule 4).
Their baseline numbers (0.949/0.821) also came from shorter, non-deck
sweep parameters, making "beat the baseline" claims incomparable. Our
pipeline's every reported value passes through `score02.py`, and the
internal-model column exists only as a cross-check against it.

## 5. Cloud validation

Winners submitted to Pasqal Cloud (EMU_FREE, 500 shots, the challenge's
hardware metric: fraction of shots that photograph an optimal independent
set). Results with batch IDs: `ch02/cloud_results_EMU_FREE.json`.

## 6. What we'd do next

- **QPU embedding**: the 5.5 µm registers don't sit on FRESNEL_CAN1's
  5.0 µm triangular lattice. The star embeds after rescaling ρ → 5.0 µm
  (blockade margins survive: 5.0 < R_b = 7.19 < 8.66); the pentagon does
  not embed in a triangular lattice at any scale — a QPU run would need
  the star only.
- **Challenge 03 bridge**: the projector-GRAPE approach is
  size-independent in formulation; the 2ᴺ propagator is the scaling wall.
  At 10–20 atoms: sparse Krylov propagation + symmetry sectors; beyond:
  tensor-network gradients (EMU_TN mirrors this on the cloud side).
