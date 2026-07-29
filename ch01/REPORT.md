# Challenge 01 — Entangle two atoms at different spacings

**Team submission · July 29, 2026 · Harmoniqs × Pasqal × Microsoft**

Target: |Ψ⁺⟩ = (|gr⟩ + |rg⟩)/√2 from |gg⟩, global drive only, within the
published `pulser.AnalogDevice` envelope (Ω ≤ 12.57 rad/µs, |δ| ≤ 125.7 rad/µs,
T ≤ 6000 ns, 4 ns clock). All fidelities below come from one scorer
(`score.py`, QuTiP emulation of the validated Pulser sequence) — the same
code path that built the submitted cloud sequences.

## Results (final — all four pulse generations)

| Pulse | T | r = 5.0 µm | r = 6.5 µm | In envelope |
|---|---|---|---|---|
| Reference (square π-pulse) | 352 ns | 0.992564 | 0.750003 | ✓ |
| v1 — analytic per-spacing | 2408/2720 ns | **0.999895** | **0.999435** | ✓ |
| v1r — one robust waveform (both r) | 2400 ns | **0.999443** | **0.997008** | ✓ |
| v2 — time-optimal (near-QSL) | 224/420 ns | **0.999999** | **0.999998** | ✓ |
| v3 — hardware-true smooth (FRESNEL bounds) | 352/600 ns | **1.000000** | **1.000000** | ✓ |

All contract-validated. Full studies: time–fidelity frontier
(`../docs/06-time-optimal.md`), noise ranking and hardware constraints
(`../docs/07-hardware.md`).

**Real-QPU validation (FRESNEL_CAN1, 500 shots, 260 ns smooth pulse,
r = 5.0 µm):** P_bell = **0.894** (447/500 shots in the entangled manifold),
01/10 symmetric within 1.5σ, blockade leakage 2.4% — within one binomial
error bar of the window pre-registered before the run. Batch
`a1a4d5e8-…` in `qpu_batch.json` / `qpu_results.json`.

### Cloud validation — Pasqal Cloud EMU_FREE, 500 shots per pulse

| Pulse | P_gg | P_gr | P_rg | P_rr | sim F |
|---|---|---|---|---|---|
| pulse_r1 | 0.000 | 0.458 | 0.542 | 0.000 | 0.99990 |
| pulse_r2 | 0.000 | 0.498 | 0.496 | 0.006 | 0.99701 |
| pulse_r2_shaped | 0.002 | 0.518 | 0.480 | 0.000 | 0.99944 |
| pulse_robust_r1 | 0.000 | 0.516 | 0.484 | 0.000 | 0.99944 |
| pulse_robust_r2 | 0.000 | 0.484 | 0.514 | 0.002 | 0.99701 |

Every pulse: ≥ 99.4% of shots in the {|gr⟩, |rg⟩} Bell manifold, double-
excitation leakage ≤ 0.6% (reference pulse at r₂: 22.4%). Populations agree
with simulation within binomial shot noise (σ ≈ 0.022 at 500 shots). Batch
IDs in `cloud_results_EMU_FREE.json`.

## Why the reference fails at r₂ — and the fix

With a global drive from |gg⟩, the dynamics lives in the symmetric ladder
|gg⟩ → |W⟩ → |rr⟩ with couplings √2·(Ω/2) and |rr⟩ shifted by V = C₆/r⁶.

- r₁ = 5.0 µm: V/Ω = 8.8 — |rr⟩ decouples, the collective π-pulse works.
- r₂ = 6.5 µm: V/Ω = 1.83 — 22% of the population leaks to |rr⟩. That is
  the entire baseline gap.

V is fixed by geometry, but **V/Ω is a control knob**: the baseline uses only
352 ns of the 6000 ns budget. Dropping Ω to 2π×0.15 MHz restores V/Ω ≈ 12 at
r₂. On top of that:

1. **Smooth sin² ramps** (~50 ns) — adiabatic w.r.t. the blockade gap,
   suppresses spectral leakage; also survives the device's modulation
   bandwidth essentially unchanged (modulated-fidelity ≥ unmodulated).
2. **Constant detuning offset** — cancels the light shift of |W⟩ from its
   dispersive coupling to |rr⟩ (fitted ≈ −Ω²·𝒪(1)/2V).
3. **Quadratic detuning ramp** (r₂ ceiling) — time-dependent δ(t) tracks the
   instantaneous shift during the ramps: 0.99701 → 0.99944.

Pulse parameters (per-spacing): Ω = 2π×0.150 MHz, T = 2408 ns (r₁) /
Ω = 2π×0.168 MHz, T = 2720 ns with δ(t) = −0.063 + 0.027·s − 0.009·(s²−⅓)
rad/µs, s ∈ [−1,1] (r₂).

## The product angle — geometry-robust entanglement

Real neutral-atom registers have per-shot position jitter and site-placement
error. Re-optimizing per spacing (what the challenge asks) is calibration
overhead; a pulse that doesn't care is a product. Our single robust waveform
maximizes min(F(r₁), F(r₂)) and holds **> 0.997 across the full 5.0–6.5 µm
range** — a 30% spacing tolerance band from one calibration, still beating
the baseline at both endpoints by construction.

The pipeline is packaged as an Amicode skill: spacing + device in →
contract-validated `pulse.toml` out → one command to Pasqal Cloud. Every
pulse here passed the extension's own `pulse_contract.py` (device limits read
from `AnalogDevice` at call time, never hardcoded).

## Reproduce

```bash
.venv/bin/python ch01/score.py                 # baselines + selftest
.venv/bin/python ch01/submit_ch01.py EMU_FREE pulse_r1 pulse_r2_shaped
```

Artifacts: `pulse_r1.toml`, `pulse_r2.toml`, `pulse_r2_shaped.toml`,
`pulse_robust_r{1,2}.toml` (contract-valid), `cloud_results_*.json`,
`analytic_*.json` (optimization traces).
