---
name: rydberg-bell-pulse
description: Prepare the two-atom Bell state |Ψ+⟩ on a neutral-atom analog device at ANY spacing r — scale Ω to restore blockade, shape δ(t) to cancel the light shift, validate through the pulse contract, submit to Pasqal Cloud. Use for Bell-state prep, spacing-robust entanglement, or as the 2-atom kernel of a larger register calibration.
agents: [researcher, experimenter]
surface: product
scenarios: [bell-state-two-atoms, spacing-change-reoptimize, geometry-robust-pulse, pasqal-cloud-validation]
---

Entangling two atoms with a global drive is a *blockade budget* problem, not a
pulse-shape search. Get V/Ω right and a smooth π-pulse does the rest; get it
wrong and no shape rescues you inside the drive envelope.

## Usage

`/rydberg-bell-pulse <spacing_um> [<spacing2_um> …] [--robust] [--submit EMU_FREE]`

The argument is: $ARGUMENTS

## The recipe (validated: F ≥ 0.9994 at r = 5.0 and 6.5 µm, AnalogDevice)

1. **Read the envelope from the device, never a slide.**
   `pulser.AnalogDevice`: C₆/ħ = 865 723 rad·µm⁶/µs, Ω ≤ 12.57 rad/µs,
   |δ| ≤ 125.7 rad/µs, T ≤ 6000 ns, 4 ns clock, r ≥ 5 µm.

2. **Pick Ω from the spacing, not the other way round.**
   V = C₆/r⁶. Demand V/Ω ≥ 9 → Ω ≤ C₆/(9·r⁶). The time budget is generous:
   T = π/(√2·Ω̄) fits T ≤ 6000 ns down to Ω ≈ 2π×0.06 MHz. At r = 6.5 µm,
   Ω = 2π×0.15 MHz gives V/Ω ≈ 12 (the naive 2π×1 MHz gives 1.8 → F = 0.75).

3. **Smooth the edges.** sin² rise/fall, ~50–600 ns. Two wins: adiabatic
   w.r.t. the blockade gap, and the device's modulation bandwidth passes it
   essentially unchanged (modulated F ≥ unmodulated — check both).

4. **Cancel the light shift with δ.** |W⟩ is pushed by its dispersive coupling
   to |rr⟩; a constant δ ≈ −𝒪(Ω²/2V) recenters the collective resonance. For
   the last ~2×10⁻³, let δ(t) = d₀ + d₁s + d₂(s²−⅓) (s ∈ [−1,1]) track the
   shift through the ramps — fit d's with Nelder-Mead against the emulator.

5. **Score ONE way.** F = |⟨Ψ⁺|ψ(T)⟩|² via QutipEmulator on the *same*
   validated Sequence you will submit — never score a waveform you didn't
   build through the contract. Basis order is ('r','g'): |rr⟩,|rg⟩,|gr⟩,|gg⟩
   = 0,1,2,3. Selftest it (idle pulse → |gg⟩) before trusting any number.

6. **Robust variant (`--robust`).** Maximize min(F(r₁), F(r₂)) over the same
   4 parameters. One waveform holds F > 0.997 across 5.0–6.5 µm — ship this
   when register geometry is uncertain; per-spacing pulses when it is not.

7. **Validate + submit.** Export 4 ns knots to `pulse.toml`
   (schema_version 1, units rad/µs, atoms [[−r/2,0],[r/2,0]]), run it through
   `pulse_contract.load_knots` + `validate_against_device`, then submit
   token-only (PASQAL_TOKEN path) with 500 runs. EMU_FREE first, always;
   QPU only behind an explicit human confirmation.

## Traps

- **Signed Ω.** Optimizers love negative amplitude; Pulser has no signed Ω —
  a sign flip is a π phase jump the device can't play on one channel.
  Constrain Ω ≥ 0 *in the optimizer*, don't clip after.
- **Off-grid durations.** Everything in multiples of the 4 ns clock or the
  contract rejects it at submit time — round *before* scoring, so the number
  you report is the number you fly.
- **Hardcoded C₆.** 862690 ≠ 865723. Read `device.interaction_coeff`.
- **Trusting the solver's fidelity.** Re-roll out the final waveform through
  an independent simulation; report only the re-rollout number.

## Worked artifacts

`~/Documents/harmoniqs-hackathon/ch01/` — score.py (scorer + selftest),
pulse_r1.toml (F=0.99990), pulse_r2_shaped.toml (F=0.99944),
pulse_robust_r{1,2}.toml (F=0.99944/0.99701), cloud_results_EMU_FREE.json,
REPORT.md. Baselines beaten: 0.9926/0.7500 → 0.9999/0.9994.
