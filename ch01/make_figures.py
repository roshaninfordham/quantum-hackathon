#!/usr/bin/env python3
"""Regenerate the evidence figures from the committed pulse artifacts.

Every curve is computed through score.bell_fidelity / the same Sequence
builder used for cloud submission — figures cannot drift from the reported
numbers. Outputs: fig_dynamics_r2.png, fig_omega_sweep.png,
fig_robustness.png, sweep_data.json.
"""

import json
import tomllib

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pulser_simulation import QutipEmulator

import score


def dynamics(amp, det, r_um, n_eval=300):
    """Time-resolved populations |rr>,|rg>,|gr>,|gg> under the pulse."""
    seq = score.build_sequence(np.asarray(amp, float), np.asarray(det, float), r_um)
    t_us = len(amp) / 1000
    emu = QutipEmulator.from_sequence(
        seq, evaluation_times=list(np.linspace(0, t_us * 0.9999, n_eval))
    )
    states = emu.run().states
    pops = np.array([[abs(s.full().ravel()[i]) ** 2 for i in range(4)] for s in states])
    return np.linspace(0, t_us, len(states)), pops


def load_pulse(name):
    """pulse.toml -> per-ns (amp, det) arrays via 4 ns zero-order hold."""
    d = tomllib.load(open(f"{name}.toml", "rb"))
    return (np.repeat(d["amplitude"][:-1], int(d["dt_ns"])),
            np.repeat(d["detuning"][:-1], int(d["dt_ns"])))


def fig_dynamics():
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    panels = [
        (axes[0], score.reference_pulse(6.5), "Reference pulse at r₂ = 6.5 µm (F = 0.750)"),
        (axes[1], load_pulse("pulse_r2_shaped"), "Our shaped pulse at r₂ = 6.5 µm (F = 0.99944)"),
    ]
    for ax, (amp, det), title in panels:
        ts, pops = dynamics(amp, det, 6.5)
        ax.plot(ts, pops[:, 3], label="P(gg)", lw=2)
        ax.plot(ts, pops[:, 1] + pops[:, 2], lw=2, color="tab:green",
                label="P(gr)+P(rg)  ← target manifold")
        ax.plot(ts, pops[:, 0], lw=2, color="tab:red",
                label="P(rr)  ← blockade leakage")
        ax.axhline(1.0, color="k", lw=.5, ls=":")
        ax.set_xlabel("t (µs)")
        ax.set_title(title, fontsize=10)
    axes[0].set_ylabel("population")
    axes[0].legend(fontsize=8)
    axes[0].annotate("22% stuck in |rr⟩", xy=(0.30, 0.24), fontsize=9, color="tab:red")
    fig.suptitle("Where the baseline loses: the doubly-excited state", fontsize=12)
    fig.tight_layout()
    fig.savefig("fig_dynamics_r2.png", dpi=150)


def fig_omega_sweep():
    """The single-knob experiment: square pi-pulse at r2, only Omega varies."""
    mhz_list = np.array([1.0, 0.8, 0.6, 0.45, 0.35, 0.3, 0.25, 0.2, 0.15, 0.1])
    fidelities, v_over_omega = [], []
    for mhz in mhz_list:
        omega = 2 * np.pi * mhz
        t = int(round(np.pi / (np.sqrt(2) * omega) * 1000 / 4)) * 4
        fid, _ = score.bell_fidelity(np.full(t, omega), np.zeros(t), 6.5)
        fidelities.append(fid)
        v_over_omega.append(score.interaction(6.5) / omega)

    fig, ax = plt.subplots(figsize=(6.5, 4))
    ax.semilogx(v_over_omega, fidelities, "o-", lw=2)
    ax.axhline(0.750003, color="tab:red", ls="--", lw=1, label="baseline (V/Ω = 1.8)")
    ax.axvline(9, color="tab:green", ls=":", lw=1, label="V/Ω = 9 design rule")
    ax.set_xlabel("V/Ω  (blockade strength, log scale)")
    ax.set_ylabel("Bell fidelity F")
    ax.set_title("Square π-pulse at r₂: fidelity is set by V/Ω alone", fontsize=11)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig("fig_omega_sweep.png", dpi=150)
    return {"Omega_MHz": [float(v) for v in mhz_list],
            "V_over_Omega": [float(v) for v in v_over_omega],
            "F": [float(v) for v in fidelities]}


def fig_robustness():
    """One fixed waveform scored across the spacing band, vs the reference."""
    rob_amp, rob_det = load_pulse("pulse_robust_r1")
    spacings = np.arange(5.0, 7.01, 0.25)
    f_rob, f_ref = [], []
    for r in spacings:
        fid, _ = score.bell_fidelity(rob_amp, rob_det, float(r))
        f_rob.append(fid)
        amp, det = score.reference_pulse(float(r))
        fid, _ = score.bell_fidelity(amp, det, float(r))
        f_ref.append(fid)

    fig, ax = plt.subplots(figsize=(6.5, 4))
    ax.plot(spacings, f_rob, "o-", lw=2, color="tab:blue", label="one robust waveform (fixed)")
    ax.plot(spacings, f_ref, "s--", lw=1.5, color="#999", label="reference pulse")
    ax.axvspan(5.0, 6.5, color="tab:green", alpha=0.08, label="challenge band r₁–r₂")
    ax.set_xlabel("atom spacing r (µm)")
    ax.set_ylabel("Bell fidelity F")
    ax.set_ylim(0.5, 1.01)
    ax.set_title("Geometry robustness: one calibration, 5.0–6.5 µm", fontsize=11)
    ax.legend(fontsize=8, loc="lower left")
    fig.tight_layout()
    fig.savefig("fig_robustness.png", dpi=150)
    return {"r_um": [float(v) for v in spacings],
            "F_robust": [float(v) for v in f_rob],
            "F_reference": [float(v) for v in f_ref]}


if __name__ == "__main__":
    fig_dynamics()
    sweep = fig_omega_sweep()
    robust = fig_robustness()
    json.dump({"omega_sweep": sweep, "robustness": robust},
              open("sweep_data.json", "w"), indent=1)
    print("wrote fig_dynamics_r2.png fig_omega_sweep.png fig_robustness.png sweep_data.json")
