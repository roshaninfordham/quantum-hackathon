# Submission — judging criteria, mapped to evidence

**Ranking rule: highest stage completed.** We completed **Challenge 01 and
Challenge 02**, both with simulation scores far above baseline and both
validated on Pasqal Cloud — including **two runs on the real FRESNEL_CAN1
QPU** (one per challenge). Every number below links to the artifact that
produced it.

## Stage score sheet

### Challenge 01 — Bell-state fidelity F vs the reference pulse

| Criterion | Reference | **Ours (best)** | Margin |
|---|---|---|---|
| F at r₁ = 5.0 µm (simulation) | 0.992564 | **1.000000** (v3, 352 ns) | +0.0074 |
| F at r₂ = 6.5 µm (simulation) | 0.750003 | **1.000000** (v3, 600 ns) | **+0.2500** |
| within device envelope | ✓ | ✓ (contract-validated, all pulses) | |
| hardware populations vs sim (500 shots) | — | 7 pulses on EMU_FREE, all within shot noise | |
| **real QPU** | — | **P_bell = 0.894** (447/500 shots entangled, 260 ns pulse) | pre-registered window hit |

Extras that differentiate: the measured time–fidelity frontier down to the
quantum speed limit (177 ns bound; we reach F = 0.999999 at 224 ns); a
noise study showing pulse duration is the dominant error channel (flips
the ranking of pulse designs); one spacing-robust waveform holding > 0.997
across the full 5.0–6.5 µm band.

→ [ch01/REPORT.md](ch01/REPORT.md) · [docs/ch01/](docs/ch01/) ·
figures: [results](ch01/ch01_results.png), [dynamics](ch01/fig_dynamics_r2.png),
[frontier](ch01/fig_time_frontier.png), [robustness](ch01/fig_robustness.png)

### Challenge 02 — P_MIS vs the baseline ramp

| Criterion | Baseline (deck ramp) | **Ours (best)** | Margin |
|---|---|---|---|
| P_MIS star K₁,₃ (simulation) | 0.727135 | **0.999998** (GRAPE, 1000 ns) | **+0.2729** |
| P_MIS cycle C₅ (simulation) | 0.657049 | **0.999999** (GRAPE, 2000 ns) | **+0.3430** |
| cloud validation (500 shots each) | — | **1500/1500 shots optimal** (3 sweeps) | |
| low-bandwidth variant (5 params, ≤ 1 MHz) | — | 0.9962 / 0.9994, cloud 498/500 & 500/500 | |
| **real QPU** (lattice-native star) | — | see [ch02/qpu_star_results.json](ch02/qpu_star_results.json) | |

Extras: C₅'s five valid answers measured near-uniform (114/98/97/96/95) —
the machine coherently samples the *entire* solution manifold; the
transfer experiment (5 parameters trained on C₅, applied unchanged, beat
the baseline on C₇ and C₉ at zero re-optimization cost — and honestly
reported failing on a cross-family instance).

→ [ch02/REPORT.md](ch02/REPORT.md) · [docs/ch02/](docs/ch02/) ·
figures: [results](ch02/fig_ch02_results.png), [low-bandwidth & transfer](ch02/fig_ch02_lowbw.png)

## Resource ledger (the "least consumption" story)

| Resource | Consumption |
|---|---|
| Optimizer compute, ch01 | full 16-point time–fidelity frontier: **5.4 s** laptop (exact 3×3 model + adjoint gradients, ~10⁶× vs naive) |
| Optimizer compute, ch02 | six GRAPE runs: ~2 min; 5-parameter CRAB sweeps: 20–45 s each, derivative-free |
| Control bandwidth | CRAB sweeps carry a **≤ 1 MHz certificate by construction** (device allows 5–8 MHz) |
| Pulse duration | 224–1000 ns vs 352–4000 ns baselines (2–4× faster ⇒ directly less decoherence) |
| Hardware shots | 500/job, the challenge's own protocol; QPU jobs gated on sim ≥ 0.99 pre-checks so no shot is spent on a pulse that could fail |
| Transfer cost | re-using a trained sweep on a new in-family graph: **one evaluation, zero optimization** |

## The presentation, in five slides

1. **The problem** — one Hamiltonian, three stages; what the baselines score
   ([docs/ch01/00-overview.md](docs/ch01/00-overview.md), [docs/ch02/01-challenge.md](docs/ch02/01-challenge.md))
2. **The diagnosis** — one number (V/Ω) explains both baseline failures;
   population-dynamics plot shows the 22% leak live ([fig](ch01/fig_dynamics_r2.png))
3. **The method** — one scorer, exact models, adjoint gradients, pre-registered
   experiments; ranking flips under noise, so we optimize for hardware, not
   for the emulator ([docs/ch01/07-hardware.md](docs/ch01/07-hardware.md))
4. **The numbers** — score sheet above; 1500/1500 cloud shots optimal on ch02;
   real-atom entanglement at 0.894
5. **The breakthrough claim (worded exactly)** — *five interpretable
   parameters, a 1 MHz bandwidth certificate, seconds of laptop compute:
   within 4×10⁻³ of broadband optimal control, transferable across a graph
   family at zero marginal cost, and validated through real hardware.* That
   pipeline — not any single fidelity — is what scales to Challenge 03.

## Method discipline

All work followed the anti-hallucination protocol in
[docs/ch01/08-prompts.md](docs/ch01/08-prompts.md): provenance for every
number, device limits read at runtime, verify-before-claim, one scorer per
challenge, declared assumptions, pre-registered predictions for both QPU
runs. The one upstream discrepancy found (a collaborator optimizer scoring
against a non-judge simulator) was caught by exactly this process and
documented in [docs/ch02/02-methods.md §4](docs/ch02/02-methods.md).
