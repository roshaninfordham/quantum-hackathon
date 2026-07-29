#!/usr/bin/env python3
"""Time-optimal Bell-state pulses via GRAPE on the exact symmetric ladder.

The physics that makes this fast: a global drive from |gg> confines the
dynamics to the 3-dim symmetric subspace {|gg>, |W>, |rr>} EXACTLY (the
antisymmetric state decouples by symmetry, not approximation). So instead of
QuTiP on the full register (~0.5 s per rollout), we propagate a 3x3
Hamiltonian with eigh-based exponentials: ~0.2 ms per rollout, ~10^3 faster.
The winner is then cross-validated in Pulser's QutipEmulator (the judge's
simulator) before anything is claimed.

    H3 = [[0,      W2,        0    ],        W2 = Omega * sqrt(2)/2
          [W2,    -delta,     W2   ],        V  = C6 / r^6
          [0,      W2,    -2*delta + V]]

Controls: Omega knots in [0, Omega_max] (first/last pinned to 0 for
modulation friendliness), delta knots in [-delta_max, +delta_max], on the
4 ns device clock. Objective: 1 - |<W|psi(T)>|^2 + lambda * sum(dOmega^2 +
ddelta^2) — the tiny smoothness term buys hardware-modulation robustness
for ~nothing in fidelity.

Minimum-time search: optimize at each T on a grid descending toward the
perfect-blockade speed limit T_QSL = pi / (sqrt(2) * Omega_max) ~ 177 ns,
and report the full T-vs-F frontier rather than a single point.
"""

import json

import numpy as np
from scipy.optimize import minimize

import score

DT_US = 0.004                                   # 4 ns clock, in us
OMEGA_MAX = score.DEVICE.channels[score.CHANNEL].max_amp        # 12.566 rad/us
DELTA_MAX = score.DEVICE.channels[score.CHANNEL].max_abs_detuning
SQ2 = np.sqrt(2.0) / 2.0


# Control-derivative generators (constant): dH/dOmega and dH/ddelta.
H_OM = SQ2 * np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]], dtype=complex)
H_DE = np.diag([0.0, -1.0, -2.0]).astype(complex)
TARGET = np.array([0.0, 1.0, 0.0], dtype=complex)          # |W>


def _step(om, de, v):
    """One knot: eigendecomposition, propagator, and dU/dOmega, dU/ddelta.

    Exact GRAPE derivative in the eigenbasis: with H = E diag(lam) E*,
    dU = E [ M o (E* Hc E) ] E*,   M_ab = (e^{-i lam_a dt} - e^{-i lam_b dt})
    / (-i dt)^{-1} ... standard divided-difference kernel (Loewner matrix).
    """
    w2 = SQ2 * om
    h = np.array([[0.0, w2, 0.0],
                  [w2, -de, w2],
                  [0.0, w2, -2 * de + v]])
    lam, e = np.linalg.eigh(h)
    ph = np.exp(-1j * lam * DT_US)
    u = (e * ph) @ e.conj().T
    dl = lam[:, None] - lam[None, :]
    m = np.where(np.abs(dl) > 1e-12,
                 (ph[:, None] - ph[None, :]) / np.where(np.abs(dl) > 1e-12, dl, 1.0),
                 -1j * DT_US * ph[:, None])
    def du(hc):
        return e @ (m * (e.conj().T @ hc @ e)) @ e.conj().T
    return u, du(H_OM), du(H_DE)


def rollout_grad(omega, delta, v):
    """Infidelity 1-|<W|psi>|^2 and its exact gradient (adjoint method).

    Cost ~ 2 rollouts total, vs ~2N rollouts for finite differences.
    """
    n = len(omega)
    us, dus_om, dus_de = [], [], []
    psis = [np.array([1.0, 0.0, 0.0], dtype=complex)]
    for k in range(n):
        u, du_om, du_de = _step(omega[k], delta[k], v)
        us.append(u); dus_om.append(du_om); dus_de.append(du_de)
        psis.append(u @ psis[-1])
    overlap = np.vdot(TARGET, psis[-1])
    fid = np.abs(overlap) ** 2
    # Backward costate: phi_k = U_{k+1}^dag ... U_N^dag |W>
    phi = TARGET.copy()
    g_om = np.zeros(n)
    g_de = np.zeros(n)
    for k in range(n - 1, -1, -1):
        g_om[k] = -2.0 * np.real(np.conj(overlap) * (phi.conj() @ (dus_om[k] @ psis[k])))
        g_de[k] = -2.0 * np.real(np.conj(overlap) * (phi.conj() @ (dus_de[k] @ psis[k])))
        phi = us[k].conj().T @ phi
    return 1.0 - fid, g_om, g_de


def propagate(omega, delta, v):
    """|gg> through the 3x3 ladder; returns final [gg, W, rr] amplitudes."""
    psi = np.array([1.0, 0.0, 0.0], dtype=complex)
    for om, de in zip(omega, delta):
        u, _, _ = _step(om, de, v)
        psi = u @ psi
    return psi


def infidelity(x, n, v, lam):
    """Objective + exact gradient for L-BFGS-B (jac=True)."""
    omega = np.concatenate(([0.0], x[: n - 2], [0.0]))   # pinned ends
    delta = x[n - 2:]
    inf, g_om, g_de = rollout_grad(omega, delta, v)
    d_om = np.diff(omega)
    d_de = np.diff(delta)
    smooth = np.sum(d_om ** 2) + np.sum(d_de ** 2)
    # d/dx of sum(diff^2): interior points get 2*(2x_k - x_{k-1} - x_{k+1})
    gs_om = np.zeros(n)
    gs_om[:-1] -= 2 * d_om
    gs_om[1:] += 2 * d_om
    gs_de = np.zeros(n)
    gs_de[:-1] -= 2 * d_de
    gs_de[1:] += 2 * d_de
    grad = np.concatenate((g_om[1:-1] + lam * gs_om[1:-1], g_de + lam * gs_de))
    return inf + lam * smooth, grad


def solve_at_duration(t_ns, r_um, lam=2e-6, restarts=3, seed=0):
    """Best (omega, delta) knot arrays at fixed duration; returns (F3, om, de)."""
    v = score.interaction(r_um)
    n = int(round(t_ns / 4))                     # knots (4 ns each)
    rng = np.random.default_rng(seed)
    best = None
    for k in range(restarts):
        om0 = np.full(n - 2, min(OMEGA_MAX * 0.8, np.pi / (np.sqrt(2) * n * DT_US)))
        om0 *= 1.0 + 0.2 * rng.standard_normal(n - 2) * (k > 0)
        de0 = 0.3 * v * (2 * rng.random(n) - 1) * (k > 0)
        x0 = np.concatenate((np.clip(om0, 0, OMEGA_MAX), np.clip(de0, -DELTA_MAX, DELTA_MAX)))
        bounds = [(0.0, OMEGA_MAX)] * (n - 2) + [(-DELTA_MAX, DELTA_MAX)] * n
        res = minimize(infidelity, x0, args=(n, v, lam), method="L-BFGS-B",
                       jac=True, bounds=bounds,
                       options=dict(maxiter=2000, maxfun=100000))
        if best is None or res.fun < best.fun:
            best = res
    omega = np.concatenate(([0.0], best.x[: n - 2], [0.0]))
    delta = best.x[n - 2:]
    psi = propagate(omega, delta, v)
    return float(np.abs(psi[1]) ** 2), omega, delta


def cross_validate(omega, delta, r_um):
    """Judge's-simulator check: expand knots to 1 ns and score in Pulser."""
    amp = np.repeat(omega, 4)
    det = np.repeat(delta, 4)
    f_plain, pops = score.bell_fidelity(amp, det, r_um)
    f_mod, _ = score.bell_fidelity(amp, det, r_um, with_modulation=True)
    return f_plain, f_mod, pops


def main():
    t_qsl = np.pi / (np.sqrt(2) * OMEGA_MAX) * 1000
    print(f"perfect-blockade QSL: T = {t_qsl:.1f} ns  (Omega_max = {OMEGA_MAX:.3f} rad/us)")
    frontier = {}
    for r_um in (5.0, 6.5):
        v = score.interaction(r_um)
        print(f"\n=== r = {r_um} um   V = {v:.2f} rad/us   V/Omega_max = {v / OMEGA_MAX:.2f} ===")
        frontier[r_um] = []
        for t_ns in (180, 200, 224, 260, 300, 352, 420, 500):
            f3, omega, delta = solve_at_duration(t_ns, r_um)
            fp, fm, _ = cross_validate(omega, delta, r_um)
            frontier[r_um].append(dict(T_ns=t_ns, F_ladder=f3, F_pulser=fp, F_mod=fm))
            print(f"  T={t_ns:4d} ns  F_ladder={f3:.6f}  F_pulser={fp:.6f}  F_mod={fm:.6f}")
            np.savez(f"fast_r{r_um}_T{t_ns}.npz", omega=omega, delta=delta)
    json.dump({str(k): v for k, v in frontier.items()},
              open("time_frontier.json", "w"), indent=1)
    print("\nwrote time_frontier.json + fast_*.npz")


if __name__ == "__main__":
    main()
