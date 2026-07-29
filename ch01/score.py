#!/usr/bin/env python3
"""Challenge 01 scorer — Bell-state fidelity for a 2-atom Rydberg register.

Single source of truth for "did we beat the reference pulse". Everything —
the analytic pulses, the Piccolo solves, the hardware comparison — is scored
through `bell_fidelity` here, so a number in the writeup cannot come from a
different simulator than a number in the plot.

Device limits are read from `pulser.AnalogDevice` at call time, never
hardcoded. The published envelope is authoritative, not the slide deck.

Conventions (verified by `selftest()`, not assumed):
  - Pulser's ground-rydberg basis is ordered ('r', 'g'), so for two atoms the
    state vector indexes as |rr>, |rg>, |gr>, |gg> = 0, 1, 2, 3.
  - Amplitude and detuning are in rad/us; durations in ns.
"""

from __future__ import annotations

import numpy as np
import pulser
from pulser_simulation import QutipEmulator

DEVICE = pulser.AnalogDevice
CHANNEL = "rydberg_global"

# Index of each two-atom basis state in the pulser state vector (basis ('r','g')).
I_RR, I_RG, I_GR, I_GG = 0, 1, 2, 3

# The reference pulse from the challenge brief (the baseline to beat).
REF_OMEGA = 2 * np.pi * 1.0      # 6.283 rad/us  (2*pi * 1.0 MHz)
REF_DELTA = 0.0                  # resonant
REF_T_NS = 352                   # pi / (sqrt(2) * Omega), rounded to the 4 ns clock

R1 = 5.0                         # um, strong blockade   (V/Omega ~ 8.8)
R2 = 6.5                         # um, weak blockade     (V/Omega ~ 1.8)


def psi_plus() -> np.ndarray:
    """|Psi+> = (|gr> + |rg>)/sqrt(2) as a dense 4-vector."""
    v = np.zeros(4, dtype=complex)
    v[I_GR] = 1 / np.sqrt(2)
    v[I_RG] = 1 / np.sqrt(2)
    return v


def interaction(r_um: float) -> float:
    """V = C6 / r^6 in rad/us, with C6 read from the device."""
    return DEVICE.interaction_coeff / r_um**6


def blockade_radius(omega: float) -> float:
    """R_b where C6 / R_b^6 == Omega."""
    return (DEVICE.interaction_coeff / omega) ** (1 / 6)


def build_register(r_um: float) -> pulser.Register:
    """Two atoms on the x-axis, straddling the origin so the register is centred."""
    if r_um < DEVICE.min_atom_distance:
        raise ValueError(
            f"spacing {r_um} um is below the device minimum "
            f"({DEVICE.min_atom_distance} um)"
        )
    return pulser.Register.from_coordinates(
        [(-r_um / 2, 0.0), (r_um / 2, 0.0)], prefix="q", center=False
    )


def build_sequence(amp_ns: np.ndarray, det_ns: np.ndarray, r_um: float) -> pulser.Sequence:
    """Per-nanosecond amplitude/detuning samples -> a validated Pulser Sequence.

    Pulser's own Sequence validation runs underneath, so an out-of-envelope
    waveform raises here rather than silently getting clipped and submitted.
    """
    amp_ns = np.asarray(amp_ns, dtype=float)
    det_ns = np.asarray(det_ns, dtype=float)
    if amp_ns.shape != det_ns.shape:
        raise ValueError(f"amp {amp_ns.shape} and det {det_ns.shape} must match")

    channel = DEVICE.channels[CHANNEL]
    duration = len(amp_ns)
    if duration % channel.clock_period:
        raise ValueError(
            f"duration {duration} ns must be a multiple of the "
            f"{channel.clock_period} ns clock"
        )
    if duration > DEVICE.max_sequence_duration:
        raise ValueError(
            f"duration {duration} ns exceeds the device cap "
            f"({DEVICE.max_sequence_duration} ns)"
        )
    if amp_ns.min() < 0:
        raise ValueError(
            f"amplitude must be non-negative (Pulser has no signed Omega); "
            f"min is {amp_ns.min():.6g}"
        )
    if amp_ns.max() > channel.max_amp:
        raise ValueError(
            f"amplitude {amp_ns.max():.6g} exceeds max_amp {channel.max_amp:.6g}"
        )
    if np.abs(det_ns).max() > channel.max_abs_detuning:
        raise ValueError(
            f"|detuning| {np.abs(det_ns).max():.6g} exceeds "
            f"max_abs_detuning {channel.max_abs_detuning:.6g}"
        )

    seq = pulser.Sequence(build_register(r_um), DEVICE)
    seq.declare_channel(CHANNEL, CHANNEL)
    seq.add(
        pulser.Pulse(
            pulser.CustomWaveform(amp_ns),
            pulser.CustomWaveform(det_ns),
            phase=0.0,
        ),
        CHANNEL,
    )
    return seq


def bell_fidelity(
    amp_ns: np.ndarray,
    det_ns: np.ndarray,
    r_um: float,
    with_modulation: bool = False,
) -> tuple[float, dict[str, float]]:
    """F = |<Psi+|psi(T)>|^2 plus the four measured populations.

    `with_modulation=True` applies the device's hardware modulation bandwidth,
    which is what the real machine actually plays. Report both.
    """
    seq = build_sequence(amp_ns, det_ns, r_um)
    emu = QutipEmulator.from_sequence(seq, with_modulation=with_modulation)
    psi = np.asarray(emu.run().get_final_state().full()).ravel()

    fidelity = float(np.abs(np.vdot(psi_plus(), psi)) ** 2)
    pops = {
        "P_gg": float(np.abs(psi[I_GG]) ** 2),
        "P_gr": float(np.abs(psi[I_GR]) ** 2),
        "P_rg": float(np.abs(psi[I_RG]) ** 2),
        "P_rr": float(np.abs(psi[I_RR]) ** 2),
    }
    return fidelity, pops


def reference_pulse(r_um: float) -> tuple[np.ndarray, np.ndarray]:
    """The challenge's baseline: square, resonant, T = pi/(sqrt(2)*Omega)."""
    amp = np.full(REF_T_NS, REF_OMEGA)
    det = np.full(REF_T_NS, REF_DELTA)
    return amp, det


def selftest() -> None:
    """Verify the basis-ordering assumption instead of trusting it."""
    # A zero-amplitude pulse must leave the system in |gg>.
    zero = np.zeros(64)
    _, pops = bell_fidelity(zero, zero, R1)
    assert pops["P_gg"] > 0.999, f"idle pulse did not stay in |gg>: {pops}"

    # Deep blockade + a pi-pulse on the collective transition must give |Psi+>,
    # which pins |gr>/|rg> to the indices we claim they have.
    omega = 2 * np.pi * 0.5
    t = int(round(np.pi / (np.sqrt(2) * omega) * 1000 / 4)) * 4
    amp = np.full(t, omega)
    fidelity, pops = bell_fidelity(amp, np.zeros(t), R1)
    assert fidelity > 0.97, f"deep-blockade pi-pulse only reached F={fidelity:.4f}"
    assert pops["P_rr"] < 0.01, f"unexpected |rr> population: {pops}"
    print(f"selftest OK  (deep-blockade check: F={fidelity:.6f})")


def main() -> None:
    selftest()

    print(f"\ndevice        {DEVICE.name}")
    print(f"C6/hbar       {DEVICE.interaction_coeff:,.2f} rad*um^6/us")
    print(f"R_b(ref)      {blockade_radius(REF_OMEGA):.3f} um")
    print(f"\nreference pulse: Omega={REF_OMEGA:.4f} rad/us, delta=0, T={REF_T_NS} ns")

    print(f"\n{'r (um)':>8} {'V (rad/us)':>12} {'V/Omega':>9} {'F_ref':>10}"
          f" {'P_gg':>9} {'P_gr':>9} {'P_rg':>9} {'P_rr':>9}")
    baselines = {}
    for r in (R1, R2):
        amp, det = reference_pulse(r)
        fidelity, pops = bell_fidelity(amp, det, r)
        baselines[r] = fidelity
        v = interaction(r)
        print(f"{r:>8.1f} {v:>12.2f} {v / REF_OMEGA:>9.2f} {fidelity:>10.6f}"
              f" {pops['P_gg']:>9.4f} {pops['P_gr']:>9.4f}"
              f" {pops['P_rg']:>9.4f} {pops['P_rr']:>9.4f}")

    print("\nTARGETS TO BEAT:")
    for r, f in baselines.items():
        print(f"  r = {r} um -> F_ref = {f:.6f}")


if __name__ == "__main__":
    main()
