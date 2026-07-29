# Hardware Reality — noise, smoothness, and the real machine

[06-time-optimal](06-time-optimal.md) ended with three open questions for the
scientists. This document answers them with computations, then takes the
result to the actual QPU.

## 1. The noise-aware ranking (the day's key scientific result)

Model: Lindblad master equation in Pulser's emulator with **Rydberg decay
τ = 100 µs** (relaxation_rate = 0.01 µs⁻¹) and **laser dephasing
0.22 µs⁻¹** (T₂* ≈ 4.5 µs). These are published-typical FRESNEL-class
values, *flagged as assumptions* — plug in the machine's calibrated numbers
and re-run (`ch01/noise_ranking.json` regenerates in seconds).

| r₂ = 6.5 µm | T | noiseless F | **F with noise** |
|---|---|---|---|
| baseline | 352 ns | 0.7500 | 0.7151 |
| v1 slow analytic | 2720 ns | 0.9994 | **0.7255 — collapses** |
| **v2 time-optimal** | 420 ns | 0.999998 | **0.9301 — wins** |
| v3 smooth (below) | 600 ns | 1.000000 | 0.9195 |

| r₁ = 5.0 µm | T | noiseless F | **F with noise** |
|---|---|---|---|
| baseline | 352 ns | 0.9926 | 0.9450 |
| v1 slow analytic | 2408 ns | 0.9999 | 0.7430 |
| v2 time-optimal | 224 ns | 0.999999 | **0.9680** |
| v3 smooth | 260 ns | 0.999991 | 0.9637 |

**The ranking flips.** In the noiseless emulator, all our pulses look alike
(0.999+). Under decoherence, the 2.4-µs pulses lose ~0.27 of fidelity —
dephasing integrates over duration — while the sub-500-ns pulses keep
0.93–0.97. Conclusion, stated as a design law: **on real hardware, pulse
duration is the noise coupling; minimize T first, then shape.** This
justifies the entire time-optimal program of doc 06 *quantitatively*.

## 2. "Smooth, don't shoot up" — the v3 pulses

The v2 pulses are bang-bang: amplitude jumps to Ω_max instantly — hard on
the EOM and outside the real machine's tighter envelope. v3 re-optimizes with
three hardware constraints (solver: same adjoint-GRAPE engine, seconds):

1. **FRESNEL-true bounds** (from the live device spec, not the challenge
   device): Ω ≤ 11.31 rad/µs, |δ| ≤ 62.8 rad/µs — both tighter than
   AnalogDevice's 12.57 / 125.7.
2. **Slew-rate cap**: |ΔΩ| ≤ 1.2 rad/µs per 4 ns knot (≈ 3× slower than the
   8 MHz modulation bandwidth requires), plus smoothness regularization —
   amplitude *rises from zero*, no jumps.
3. **Pinned endpoints**: Ω(0) = Ω(T) = 0.

| v3 pulse | T | F (Pulser) | F (modulated) | max slew (rad/µs/knot) |
|---|---|---|---|---|
| r₁ = 5.0 µm | 260 ns | 0.999991 | 0.999645 | 1.20 |
| r₁ = 5.0 µm | **352 ns** | **1.000000** | **0.999997** | 0.66 |
| r₂ = 6.5 µm | **600 ns** | **1.000000** | **0.999852** | 0.62 |

Note the poetry: at the baseline's own 352 ns, the smooth hardware-true
pulse is numerically perfect where the baseline scores 0.9926/0.7500.

## 3. What the real machine actually allows (found the hard way)

Facts pulled live from the cloud device specs — none of this is on the
challenge slide:

- **FRESNEL**: Ω_max 11.31, |δ|_max 62.8, mod. bandwidth 8 MHz,
  `requires_layout` on TriangularLatticeLayout(120, 5 µm) — and a **minimum
  filling of 42 qubits**, so a 2-atom register is *rejected* (we hit
  `MinQubitNumberError`).
- **FRESNEL_CAN1**: carries the minimum-size 60-trap layout, which pulser
  exempts from the filling rule — **the only 2-atom QPU path**. Ω_max 12.57,
  |δ|_max 62.8, mod. bandwidth 5 MHz.
- **Triangular lattice, 5 µm pitch** ⇒ achievable pair spacings are 5.0,
  8.66, 10.0… µm. **r₂ = 6.5 µm cannot exist on this hardware.** Challenge
  scoring (AnalogDevice, simulation) is unaffected; hardware validation is
  therefore an r₁ = 5.0 µm story.

## 4. The QPU run

Submitted: **v3 @ 260 ns** (the shortest FRESNEL-flyable smooth pulse; best
noise score among flyable candidates, 0.9637) on **FRESNEL_CAN1**, two traps
5.0 µm apart from the calibrated 60-trap layout, 500 shots. Batch
`a1a4d5e8-b3d1-4e74-be6a-6b2ebb366e34` (`ch01/qpu_batch.json`).

**Measured — real atoms** (`ch01/qpu_results.json`), against the predictions
pre-registered above the run:

| | P_gg | P_gr | P_rg | **P_bell** | P_rr |
|---|---|---|---|---|---|
| noiseless prediction | 0.000 | 0.500 | 0.500 | 1.000 | 0.000 |
| + assumed noise | ~0.02 | — | — | ~0.96 | ~0.01 |
| + SPAM (unmodeled) | — | — | — | **0.90–0.95 window** | — |
| **QPU, 500 shots** | 0.082 | 0.464 | 0.430 | **0.894** | **0.024** |

Readings: **447/500 real-world shots in the entangled manifold**; the
01/10 split symmetric within 1.5σ (exchange symmetry survives on hardware);
blockade leakage 2.4%, matching the noise band. P_bell lands 0.6% below the
pre-registered window's lower edge — within one binomial error bar
(±2.2%) of it, with the gap plausibly the unmodeled state-prep error. The
prediction chain (noiseless → +noise → +SPAM → measured) degrades exactly
as the model says it should — that traceability, not the raw number, is
the result.

## 5. Independent cross-validation (teammate's Julia/Piccolo work)

`piccolo-solutions/` (pushed by a teammate) solves the same problem with a
completely different stack — Julia, Piccolo.jl, Ipopt interior-point NLP —
and lands on the same physics:

| Point | Piccolo (Julia/Ipopt) | Ours (NumPy adjoint-GRAPE) |
|---|---|---|
| r₁ fixed-time | F = 0.99999996 @ 500 ns | F = 1.000000 @ 352–500 ns |
| r₂ min-time | F = 0.99998 @ **377 ns** | frontier: 0.9979 @ 352 → 0.999998 @ 420 |

Their 377 ns minimum-time point sits exactly on our measured frontier —
two independent solvers, one physical speed limit. Their README's pending
item (slope/acceleration-bounded re-solve) is delivered here as v3.

## 6. Beyond populations: certifying entanglement (future work, costed)

Populations cannot distinguish |Ψ⁺⟩ from a classical 50/50 mixture of
|gr⟩ and |rg⟩ ([05-methods §8](05-methods.md)). Two upgrades, honestly
assessed:

- **Bell-inequality (CHSH) violation: not implementable here at any shot
  count.** CHSH needs each atom measured along its *own* rotated axis;
  our drive is global, so only same-angle correlators E(θ,θ) exist — no
  CHSH combination can be formed. (With local addressing and our measured
  visibility ~0.8, S ≈ 2.26 would need ~1,400 shots for 3σ; a perfect
  state needs only ~105.)
- **Entanglement witness via parity oscillation: one more 500-shot job.**
  Append a global π/2 analysis pulse with swept phase; the |gr⟩↔|rg⟩
  coherence appears as a parity oscillation, and F > 0.5 certifies genuine
  entanglement (standard Sackett-et-al. protocol; global drive suffices).
  At our F ≈ 0.89 the 3σ certification needs only ~10² shots — one job
  upgrades the claim from "populations match" to "entanglement certified
  on real atoms."

## Answers to doc 06's open questions

1. **Noise model ranking** → done (§1): short wins; v2/v3 are the hardware
   pulses, v1 is the pedagogy pulse.
2. **EOM slew limits** → v3 satisfies a 1.2 rad/µs/knot cap with F_mod ≥
   0.9996; constraint is cheap (seconds to re-solve for any cap the
   hardware team names).
3. **Headline number** → noise-weighted: **~0.96 expected on hardware at
   r₁**, with the noiseless 0.999999 as the model ceiling. Both reported,
   never conflated.
