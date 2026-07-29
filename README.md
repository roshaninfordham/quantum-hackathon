# Quantum Hackathon — Challenge 01: Entangle two atoms at different spacings

**Harmoniqs × Pasqal × Microsoft · July 29 2026 · Microsoft Garage NYC**

Prepare |Ψ⁺⟩ = (|gr⟩ + |rg⟩)/√2 on two neutral atoms with a single global
pulse, beating the reference pulse at r₁ = 5.0 µm **and** r₂ = 6.5 µm inside
the published `pulser.AnalogDevice` envelope.

## Results

| Pulse | r₁ = 5.0 µm | r₂ = 6.5 µm | Status |
|---|---|---|---|
| Reference (baseline) | 0.992564 | 0.750003 | — |
| **Ours, per-spacing** | **0.999895** | **0.999435** | ✅ cloud-validated |
| **Ours, one robust waveform** | **0.999443** | **0.997008** | ✅ cloud-validated |

All five pulses validated on **Pasqal Cloud** (EMU_FREE, 500 shots each):
≥ 99.4% of shots in the Bell manifold, |rr⟩ leakage ≤ 0.6% (baseline at r₂:
22.4%). Populations match simulation within shot noise.

![Results](ch01/ch01_results.png)

## The one-line insight

The baseline fails at r₂ purely because V/Ω = 1.8 — weak blockade leaks 22%
into |rr⟩. V is fixed by geometry, but **V/Ω is a control knob**: slow the
drive (the 6 µs budget allows 17× the baseline duration), smooth the edges,
and cancel the light shift with δ(t). Full story: [docs/02-physics.md](docs/02-physics.md).

## Repo map

```
ch01/
  score.py               one scorer for everything (device-validated, selftested)
  pasqal_login.py        interactive login → short-lived token (human runs this)
  pasqal_client.py       token-only SDK client (agent uses this)
  submit_ch01.py         pulse.toml → Pasqal Cloud batch → measured populations
  pulse_*.toml           contract-valid pulse artifacts (the submissions)
  cloud_results_*.json   measured counts + batch IDs
  analytic_*.json        optimization traces
  REPORT.md              the submission report
  ch01_results.png       pulses + baseline comparison + cloud-vs-sim
docs/
  01-challenge.md        the task and the device envelope
  02-physics.md          why the baseline fails, why our fix is simple
  03-process.md          what we did, in order, with the decisions
  04-product.md          the commercial angle: geometry-robust entanglement
skills/
  rydberg-bell-pulse/    the Amicode skill (recipe + traps + artifacts)
```

## Reproduce

```bash
python3 -m venv .venv && .venv/bin/pip install pulser pulser-simulation pasqal-cloud scipy
.venv/bin/python ch01/score.py                    # baselines + selftest
.venv/bin/python ch01/pasqal_login.py <email>     # interactive; token → 0600 file
.venv/bin/python ch01/submit_ch01.py EMU_FREE pulse_r1 pulse_r2_shaped
```

## Toolchain

[Amicode](https://harmoniqs.co) (Harmoniqs' agentic control extension) for
the problem/run/contract scaffolding, [Pulser](https://pulser.readthedocs.io)
+ QuTiP for simulation, [pasqal-cloud](https://docs.pasqal.com/cloud/) for
hardware access.
