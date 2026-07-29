# The Challenge

**A Real Quantum Hackathon** — Harmoniqs × Pasqal × Microsoft, July 29 2026,
Microsoft Garage NYC. Three stages, one control problem: a register of neutral
atoms evolving under the analog-mode Rydberg Hamiltonian, driven by a single
global pulse. Ranking = highest stage completed.

## The Hamiltonian

```
H(t)/ħ = (Ω(t)/2) Σᵢ σₓ⁽ⁱ⁾ − δ(t) Σᵢ nᵢ + Σᵢ<ⱼ (C₆/ħrᵢⱼ⁶) nᵢnⱼ
```

- `Ω(t)`, `δ(t)` — **global**: every atom sees the same waveforms
- `nᵢ = |r⟩⟨r|ᵢ` — Rydberg excitation number of atom i
- `rᵢⱼ` — fixed by the register layout (positions are also controls)
- Blockade radius `R_b`: the spacing where interaction equals drive,
  `C₆/R_b⁶ = ħΩ`

## Challenge 01 — Entangle two atoms at different spacings

Prepare the Bell state **|Ψ⁺⟩ = (|gr⟩ + |rg⟩)/√2** from |gg⟩:

- at **r₁ = 5.0 µm** (V/Ω = 8.8 under the reference pulse — strong blockade)
- at **r₂ = 6.5 µm** (V/Ω = 1.8 — weak blockade), re-optimizing the waveforms

**Score**: Bell fidelity F = |⟨Ψ⁺|ψ(T)⟩|² in simulation; hardware validation
compares measured two-atom populations P_gg, P_gr, P_rg, P_rr against sim
(500 shots). **Success**: F above the reference pulse at both spacings,
within the device envelope.

### The reference pulse (baseline to beat)

| Parameter | Value |
|---|---|
| Ω | 2π × 1.0 MHz, square, resonant (δ = 0) |
| T | 352 ns = π/(√2·Ω) |
| F at r₁ | **0.992564** (near-optimal) |
| F at r₂ | **0.750003** (leaks to \|rr⟩ — that's the gap to close) |

## Device envelope (`pulser.AnalogDevice` — authoritative, read at runtime)

| Limit | Value |
|---|---|
| C₆/ħ | 865 723.02 rad·µs⁻¹·µm⁶ (Rydberg level 60) |
| Ω max | 12.566 rad/µs (2π × 2 MHz) |
| \|δ\| max | 125.66 rad/µs (2π × 20 MHz) |
| T max | 6 000 ns (hard cap, all challenges) |
| clock | 4 ns (all durations multiples of 4 ns) |
| min atom spacing | 5 µm |
| register | ≤ 80 atoms, ≤ 38 µm from origin |
| shots | 2 000 runs/job hardware budget |

> The slide deck's numbers are illustrative; the published device envelope is
> authoritative. Our tooling reads every limit from the `Device` object at
> call time — one of the bundled templates hardcoded C₆ = 862 690 (0.35% off)
> and Ω bounds 8× over the envelope, which validation would have rejected.
