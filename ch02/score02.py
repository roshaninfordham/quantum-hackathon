#!/usr/bin/env python3
"""Challenge 02 scorer — P_MIS for unit-disk graphs on 4-5 atom registers.

Same discipline as ch01/score.py: ONE scorer, device limits read from
pulser.AnalogDevice at call time, conventions verified by selftest, every
reported number produced here.

Graphs (from the challenge deck):
  G_A star K_{1,3}: 4 atoms, center + 3 leaves at rho = 5.5 um, 120 deg
      apart. Edges: center-leaf (5.5 < R_b); non-edges: leaf-leaf
      (sqrt(3)*5.5 = 9.53 > R_b). alpha = 3; unique MIS = the three leaves.
  G_B cycle C_5: 5 atoms, regular pentagon, side s = 5.5 um
      (circumradius s / (2 sin(pi/5)) = 4.68 um). Edges: sides
      (5.5 < R_b); non-edges: diagonals (1.618*5.5 = 8.90 > R_b).
      alpha = 2; five MIS's (the five non-adjacent vertex pairs).

Baseline (deck): T = 4000 ns, Omega = 2pi*1.0 MHz trapezoid with 252 ns
rise/fall (ASSUMED linear ramps - the deck states only "252 ns rise/fall"),
delta linear from -2pi*2.0 to +2pi*2.0 MHz. Final detuning sits inside the
MIS window U_diag < delta_f < U_nn (1.74 < 12.57 < 31.31 rad/us for the
pentagon), as the deck requires.

P_MIS = sum of |<b|psi(T)>|^2 over bitstrings b that are independent sets
of size alpha(G). Qubit i's bit is 1 iff atom i measured in |r>.
"""

from __future__ import annotations

import itertools

import numpy as np
import pulser
from pulser_simulation import QutipEmulator

DEVICE = pulser.AnalogDevice
CHANNEL = "rydberg_global"

# Deck baseline parameters
T_NS = 4000
OMEGA_B = 2 * np.pi * 1.0          # rad/us
RISE_NS = 252
DELTA_0 = -2 * np.pi * 2.0         # rad/us
DELTA_F = +2 * np.pi * 2.0
SPACING = 5.5                       # um, both registers


def star_register() -> tuple[pulser.Register, list[tuple[int, int]], int]:
    """K_{1,3}: qubit 0 = center, 1-3 = leaves. Returns (register, edges, alpha)."""
    coords = [(0.0, 0.0)]
    for k in range(3):
        th = np.pi / 2 + 2 * np.pi * k / 3
        coords.append((SPACING * np.cos(th), SPACING * np.sin(th)))
    reg = pulser.Register.from_coordinates(coords, prefix="q", center=False)
    return reg, [(0, 1), (0, 2), (0, 3)], 3


def cycle_register() -> tuple[pulser.Register, list[tuple[int, int]], int]:
    """C_5: regular pentagon with side SPACING."""
    rad = SPACING / (2 * np.sin(np.pi / 5))
    coords = [(rad * np.cos(np.pi / 2 + 2 * np.pi * k / 5),
               rad * np.sin(np.pi / 2 + 2 * np.pi * k / 5)) for k in range(5)]
    reg = pulser.Register.from_coordinates(coords, prefix="q", center=False)
    return reg, [(k, (k + 1) % 5) for k in range(5)], 2


GRAPHS = {"star_K13": star_register, "cycle_C5": cycle_register}


def check_unit_disk(reg: pulser.Register, edges: list, omega: float) -> None:
    """Verify the register induces exactly the target graph at blockade R_b."""
    rb = (DEVICE.interaction_coeff / omega) ** (1 / 6)
    qubits = list(reg.qubits.values())
    edge_set = {tuple(sorted(e)) for e in edges}
    for i, j in itertools.combinations(range(len(qubits)), 2):
        d = float(np.linalg.norm(np.array(qubits[i]) - np.array(qubits[j])))
        is_edge = (i, j) in edge_set
        if is_edge and d >= rb:
            raise ValueError(f"target edge ({i},{j}) at {d:.2f} um >= R_b {rb:.2f}")
        if not is_edge and d <= rb:
            raise ValueError(f"non-edge ({i},{j}) at {d:.2f} um <= R_b {rb:.2f}")


def mis_bitstrings(n: int, edges: list, alpha: int) -> list[int]:
    """State-vector indices of all size-alpha independent sets.

    Convention (verified by selftest): pulser/qutip per-qubit basis order is
    (|r>, |g>) with qubit 0 most significant — so |g...g> is the LAST index
    (2^n - 1) and exciting atom q CLEARS bit (n-1-q).
    """
    edge_set = {tuple(sorted(e)) for e in edges}
    out = []
    for subset in itertools.combinations(range(n), alpha):
        if any(tuple(sorted(p)) in edge_set for p in itertools.combinations(subset, 2)):
            continue
        idx = (2 ** n - 1) - sum(1 << (n - 1 - q) for q in subset)
        out.append(idx)
    return out


def excitation_pattern(idx: int, n: int) -> str:
    """Index -> human-readable bitstring with 1 = |r> (matches QPU output)."""
    return format((2 ** n - 1) ^ idx, f"0{n}b")


def build_sequence(amp_ns, det_ns, reg: pulser.Register) -> pulser.Sequence:
    amp_ns = np.asarray(amp_ns, float)
    det_ns = np.asarray(det_ns, float)
    ch = DEVICE.channels[CHANNEL]
    if len(amp_ns) % ch.clock_period or len(amp_ns) != len(det_ns):
        raise ValueError("waveforms must share a clock-multiple length")
    if amp_ns.min() < 0 or amp_ns.max() > ch.max_amp:
        raise ValueError(f"amplitude out of [0, {ch.max_amp:.4g}]")
    if np.abs(det_ns).max() > ch.max_abs_detuning:
        raise ValueError(f"|detuning| exceeds {ch.max_abs_detuning:.4g}")
    if len(amp_ns) > DEVICE.max_sequence_duration:
        raise ValueError("exceeds max sequence duration")
    seq = pulser.Sequence(reg, DEVICE)
    seq.declare_channel(CHANNEL, CHANNEL)
    seq.add(pulser.Pulse(pulser.CustomWaveform(amp_ns),
                         pulser.CustomWaveform(det_ns), phase=0.0), CHANNEL)
    return seq


def p_mis(amp_ns, det_ns, graph: str) -> tuple[float, dict]:
    """P_MIS plus diagnostics (per-MIS probabilities, top leak states)."""
    reg, edges, alpha = GRAPHS[graph]()
    n = len(reg.qubits)
    seq = build_sequence(amp_ns, det_ns, reg)
    psi = np.asarray(QutipEmulator.from_sequence(seq).run()
                     .get_final_state().full()).ravel()
    probs = np.abs(psi) ** 2
    idxs = mis_bitstrings(n, edges, alpha)
    val = float(probs[idxs].sum())
    top = np.argsort(probs)[::-1][:4]
    diag = {
        "per_mis": {excitation_pattern(i, n): float(probs[i]) for i in idxs},
        "top_states": {excitation_pattern(i, n): float(probs[i]) for i in top},
    }
    return val, diag


def baseline_waveforms() -> tuple[np.ndarray, np.ndarray]:
    """The deck's baseline ramp, on the 1 ns grid."""
    t = np.arange(T_NS, dtype=float)
    amp = np.full(T_NS, OMEGA_B)
    amp[:RISE_NS] = OMEGA_B * t[:RISE_NS] / RISE_NS
    amp[T_NS - RISE_NS:] = OMEGA_B * (T_NS - t[T_NS - RISE_NS:]) / RISE_NS
    det = DELTA_0 + (DELTA_F - DELTA_0) * t / (T_NS - 1)
    return amp, det


def selftest() -> None:
    # (a) zero pulse keeps |g...g> -> index 0, P_MIS = 0.
    zero = np.zeros(64)
    for graph in GRAPHS:
        reg, edges, alpha = GRAPHS[graph]()
        seq = build_sequence(zero, zero, reg)
        psi = np.asarray(QutipEmulator.from_sequence(seq).run()
                         .get_final_state().full()).ravel()
        assert abs(psi[-1]) ** 2 > 0.999, f"idle drifted for {graph}"
    # (b) both registers realize exactly their target unit-disk graph.
    for graph in GRAPHS:
        reg, edges, _ = GRAPHS[graph]()
        check_unit_disk(reg, edges, OMEGA_B)
    # (c) MIS enumeration sanity: star has exactly 1, C5 exactly 5.
    assert len(mis_bitstrings(4, [(0, 1), (0, 2), (0, 3)], 3)) == 1
    assert len(mis_bitstrings(5, [(k, (k + 1) % 5) for k in range(5)], 2)) == 5
    print("selftest OK")


def main() -> None:
    selftest()
    rb = (DEVICE.interaction_coeff / OMEGA_B) ** (1 / 6)
    print(f"\nR_b(Omega_b) = {rb:.3f} um; U_nn = "
          f"{DEVICE.interaction_coeff / SPACING**6:.2f}, U_diag(C5) = "
          f"{DEVICE.interaction_coeff / (1.6180339887 * SPACING)**6:.2f} rad/us; "
          f"delta_f = {DELTA_F:.2f} rad/us")
    amp, det = baseline_waveforms()
    print(f"\nBASELINE (deck ramp, T = {T_NS} ns):")
    for graph in GRAPHS:
        val, diag = p_mis(amp, det, graph)
        print(f"  {graph:9s}  P_MIS = {val:.6f}   per-MIS: "
              f"{ {k: round(v, 4) for k, v in diag['per_mis'].items()} }")


if __name__ == "__main__":
    main()
