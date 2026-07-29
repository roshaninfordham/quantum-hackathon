# Challenge 01 — Entangling two atoms with one global pulse

**Harmoniqs × Pasqal × Microsoft quantum hackathon · July 29 2026 · Microsoft Garage NYC**

This repository is a complete, reproducible solution to Challenge 01:
prepare the Bell state **|Ψ⁺⟩ = (|gr⟩ + |rg⟩)/√2** on two neutral atoms at
two different spacings, beating the starter-kit reference pulse at both,
inside the real device's published limits — validated on Pasqal Cloud.

| | r₁ = 5.0 µm | r₂ = 6.5 µm | evidence |
|---|---|---|---|
| Reference pulse (baseline) | 0.992564 | 0.750003 | [score.py](ch01/score.py) |
| **Ours, per-spacing** | **0.999895** | **0.999435** | [REPORT.md](ch01/REPORT.md) |
| **Ours, one robust waveform** | **0.999443** | **0.997008** | [fig_robustness.png](ch01/fig_robustness.png) |
| **Ours, time-optimal (224 / 420 ns — 6–11× shorter)** | **0.999999** | **0.999998** | [docs/06-time-optimal.md](docs/06-time-optimal.md) |
| Cloud validation (500 shots ea.) | ✅ | ✅ | [cloud_results](ch01/cloud_results_EMU_FREE.json) |

![Results](ch01/ch01_results.png)

---

## From first principles, in five steps

**1 · The qubit.** Each atom is a two-level system: ground |g⟩ and a highly
excited *Rydberg* state |r⟩. A laser couples them with Rabi frequency Ω(t)
(how hard we drive) and detuning δ(t) (how far off-resonance). Both knobs are
**global** — every atom sees the same light. *→ [docs/01-challenge.md](docs/01-challenge.md)*

**2 · The interaction.** Two atoms in |r⟩ repel: energy V = C₆/r⁶. At close
spacing this shift is so large the laser cannot excite both — the **Rydberg
blockade**. Blockade radius R_b ≈ 7.2 µm here; both our spacings sit inside it,
but not equally deep. *→ [docs/01-challenge.md](docs/01-challenge.md)*

**3 · Why blockade creates entanglement.** Driving both atoms from |gg⟩, the
blockade forbids |rr⟩, so the system oscillates between |gg⟩ and the *shared*
single excitation (|gr⟩+|rg⟩)/√2 — which **is** the Bell state we're asked
for. The oscillation runs √2 faster than a single atom (both atoms reach for
the same photon). Stop at the π-pulse time T = π/(√2Ω): done.
*→ [docs/02-physics.md](docs/02-physics.md), derivation in [docs/05-methods.md §2](docs/05-methods.md)*

**4 · Why the baseline breaks at r₂ — the one number that matters.** Blockade
quality is the ratio **V/Ω**. The reference pulse (Ω = 2π×1 MHz) gives
V/Ω = 8.8 at r₁ (fine: F = 0.993) but **1.83** at r₂ — the "forbidden" |rr⟩
takes 22% of the population and F collapses to 0.75. See it happen:
[fig_dynamics_r2.png](ch01/fig_dynamics_r2.png).
*→ single-knob proof: [fig_omega_sweep.png](ch01/fig_omega_sweep.png), [docs/05-methods.md §4](docs/05-methods.md)*

**5 · The fix.** V is fixed by geometry, but Ω is ours: slow down (V/Ω ≥ 9),
smooth the edges (sin² ramps), and cancel the small energy shift of the target
state with δ(t) — a shift our optimizer rediscovered to three digits of the
perturbation-theory value Ω²/2V. Result: ≥ 0.9994 at both spacings.
*→ [docs/02-physics.md](docs/02-physics.md), all parameters in [docs/05-methods.md §5](docs/05-methods.md)*

**6 · Then make it fast.** Slowing down costs coherence on real hardware. Using
optimal control (GRAPE with exact adjoint gradients on the exact 3-state
symmetric model — the full 16-point time–fidelity frontier computes in 5.4 s),
we push to the quantum speed limit: **F = 0.999999 at 224 ns (r₁) and 420 ns
(r₂)** — 6–11× shorter than step 5, near the theoretical bound T = π/(√2·Ω_max)
= 177 ns. *→ [docs/06-time-optimal.md](docs/06-time-optimal.md), frontier:
[fig_time_frontier.png](ch01/fig_time_frontier.png)*

---

## Reading paths

| You are… | Read, in order |
|---|---|
| **Anyone** (10 min) | this page → [02-physics](docs/02-physics.md) |
| **Reviewing the science** | [05-methods](docs/05-methods.md) — every number traced to source, derivations, error analysis — then [06-time-optimal](docs/06-time-optimal.md) for the speed-limit study |
| **Reviewing the engineering** | [03-process](docs/03-process.md) → [ch01/score.py](ch01/score.py) → [ch01/submit_ch01.py](ch01/submit_ch01.py) |
| **Asking "so what?"** | [04-product](docs/04-product.md) — geometry-robust entanglement as the product |
| **Judging the challenge** | [ch01/REPORT.md](ch01/REPORT.md) — the formal submission |

## Everything in this repo

| Artifact | What it is |
|---|---|
| [ch01/score.py](ch01/score.py) | **The one scorer.** Device-validated Pulser sequence → QuTiP fidelity. Selftests its own basis conventions. Every number in every doc came from here. |
| [ch01/pulse_r1.toml](ch01/pulse_r1.toml) · [pulse_r2.toml](ch01/pulse_r2.toml) · [pulse_r2_shaped.toml](ch01/pulse_r2_shaped.toml) | Per-spacing optimized pulses (4 ns knots, contract-valid) |
| [ch01/pulse_robust_r1.toml](ch01/pulse_robust_r1.toml) · [pulse_robust_r2.toml](ch01/pulse_robust_r2.toml) | The single spacing-robust waveform, registered at each spacing |
| [ch01/pulse_r1_fast.toml](ch01/pulse_r1_fast.toml) · [pulse_r2_fast.toml](ch01/pulse_r2_fast.toml) | Time-optimal pulses (224 / 420 ns), near the quantum speed limit |
| [ch01/time_frontier.json](ch01/time_frontier.json) · [fig_time_frontier.png](ch01/fig_time_frontier.png) | The measured time–fidelity frontier at both spacings |
| [ch01/cloud_results_EMU_FREE.json](ch01/cloud_results_EMU_FREE.json) | Measured counts from Pasqal Cloud, 500 shots/pulse, with batch IDs |
| [ch01/make_figures.py](ch01/make_figures.py) | Regenerates every figure from the committed artifacts |
| [ch01/fast_opt.py](ch01/fast_opt.py) | Time-optimal GRAPE on the exact 3×3 symmetric ladder (~10³× faster than full-space simulation) |
| [ch01/analytic_*.json](ch01/) · [sweep_data.json](ch01/sweep_data.json) | Raw optimization traces and sweep data behind the plots |
| [ch01/pasqal_login.py](ch01/pasqal_login.py) · [pasqal_client.py](ch01/pasqal_client.py) · [submit_ch01.py](ch01/submit_ch01.py) | Cloud pipeline: interactive login → short-lived token → token-only submission |
| [skills/rydberg-bell-pulse/SKILL.md](skills/rydberg-bell-pulse/SKILL.md) | The recipe + traps, packaged as an Amicode skill |
| [docs/](docs/) | The five documents linked throughout this page |

## Reproduce

```bash
python3 -m venv .venv
.venv/bin/pip install pulser pulser-simulation pasqal-cloud scipy
.venv/bin/python ch01/score.py           # constants, baselines, selftest
.venv/bin/python ch01/make_figures.py    # regenerate all evidence figures
# cloud (your own project):
export PASQAL_PROJECT_ID=<your-project-id>
.venv/bin/python ch01/pasqal_login.py <email>       # interactive, token-only after this
.venv/bin/python ch01/submit_ch01.py EMU_FREE pulse_r1 pulse_r2_shaped
```

Toolchain: [Amicode](https://harmoniqs.co) (problem/run/contract scaffolding) ·
[Pulser](https://pulser.readthedocs.io) + QuTiP (simulation) ·
[pasqal-cloud](https://docs.pasqal.com/cloud/) (hardware access).
