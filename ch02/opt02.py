#!/usr/bin/env python3
"""Challenge 02 optimizer — full-space adjoint GRAPE maximizing P_MIS.

Same engine as ch01/fast_opt.py, generalized two ways:
  - N-qubit full Hilbert space (16/32-dim; exact, no blockade approximation,
    diagonal interaction tails included);
  - projector objective P_MIS = <psi|P|psi> instead of a single-state
    overlap (the C_5 target is a 5-fold degenerate manifold).

Controls: Omega/delta knots on an 8 ns grid (2x the device clock — halves
compute, still exactly representable), Omega pinned to 0 at both ends,
device bounds from pulser.AnalogDevice. Warm-started from the deck's
baseline ramp (best practice per the warm-start doctrine, and it puts the
optimizer in the adiabatic basin rather than a random one).

Every winner is cross-validated through ch02/score02.py (the judge-facing
Pulser scorer) before being reported; the adjoint gradient is verified
against finite differences at import time of the main routine.
"""

import json

import numpy as np
from scipy.optimize import minimize

import score02

DT_NS = 8
DT_US = DT_NS / 1000.0
OMEGA_MAX = score02.DEVICE.channels[score02.CHANNEL].max_amp
DELTA_MAX = score02.DEVICE.channels[score02.CHANNEL].max_abs_detuning


def build_operators(graph: str):
    """H = om*HX + de*HD + HINT in the (0=g, 1=r) computational basis."""
    reg, edges, alpha = score02.GRAPHS[graph]()
    coords = [np.array(v) for v in reg.qubits.values()]
    n = len(coords)
    dim = 2 ** n
    hx = np.zeros((dim, dim))
    hd = np.zeros(dim)
    hint = np.zeros(dim)
    c6 = score02.DEVICE.interaction_coeff
    for state in range(dim):
        bits = [(state >> (n - 1 - q)) & 1 for q in range(n)]
        hd[state] = -sum(bits)
        for i in range(n):
            for j in range(i + 1, n):
                if bits[i] and bits[j]:
                    hint[state] += c6 / np.linalg.norm(coords[i] - coords[j]) ** 6
        for q in range(n):                       # sigma_x flips qubit q
            hx[state ^ (1 << (n - 1 - q)), state] += 0.5
    # MIS projector indices in THIS basis (bit=1 means |r>).
    edge_set = {tuple(sorted(e)) for e in edges}
    idxs = []
    import itertools
    for subset in itertools.combinations(range(n), alpha):
        if not any(tuple(sorted(p)) in edge_set
                   for p in itertools.combinations(subset, 2)):
            idxs.append(sum(1 << (n - 1 - q) for q in subset))
    return hx, hd, hint, np.array(idxs), n


def make_rollout(hx, hd, hint, mis_idx):
    dim = hx.shape[0]

    def step(om, de):
        h = om * hx + np.diag(de * hd + hint)
        lam, e = np.linalg.eigh(h)
        ph = np.exp(-1j * lam * DT_US)
        u = (e * ph) @ e.conj().T
        dl = lam[:, None] - lam[None, :]
        m = np.where(np.abs(dl) > 1e-12,
                     (ph[:, None] - ph[None, :]) / np.where(np.abs(dl) > 1e-12, dl, 1.0),
                     -1j * DT_US * ph[:, None])
        du_om = e @ (m * (e.conj().T @ hx @ e)) @ e.conj().T
        du_de = e @ (m * (e.conj().T @ np.diag(hd) @ e)) @ e.conj().T
        return u, du_om, du_de

    def rollout_grad(omega, delta):
        k = len(omega)
        psi = np.zeros(dim, complex)
        psi[0] = 1.0                              # |g...g>
        us, dom, dde, psis = [], [], [], [psi]
        for i in range(k):
            u, a, b = step(omega[i], delta[i])
            us.append(u); dom.append(a); dde.append(b)
            psis.append(u @ psis[-1])
        pn = psis[-1]
        pmis = float(np.sum(np.abs(pn[mis_idx]) ** 2))
        chi = np.zeros(dim, complex)
        chi[mis_idx] = pn[mis_idx]                # P|psi_N>
        g_om = np.zeros(k); g_de = np.zeros(k)
        for i in range(k - 1, -1, -1):
            g_om[i] = -2.0 * np.real(chi.conj() @ (dom[i] @ psis[i]))
            g_de[i] = -2.0 * np.real(chi.conj() @ (dde[i] @ psis[i]))
            chi = us[i].conj().T @ chi
        return 1.0 - pmis, g_om, g_de

    return rollout_grad


def objective(x, k, rollout, lam):
    omega = np.concatenate(([0.0], x[:k - 2], [0.0]))
    delta = x[k - 2:]
    inf, g_om, g_de = rollout(omega, delta)
    d_om, d_de = np.diff(omega), np.diff(delta)
    gs_om = np.zeros(k); gs_om[:-1] -= 2 * d_om; gs_om[1:] += 2 * d_om
    gs_de = np.zeros(k); gs_de[:-1] -= 2 * d_de; gs_de[1:] += 2 * d_de
    grad = np.concatenate((g_om[1:-1] + lam * gs_om[1:-1], g_de + lam * gs_de))
    return inf + lam * (np.sum(d_om ** 2) + np.sum(d_de ** 2)), grad


def verify_gradient(rollout) -> float:
    rng = np.random.default_rng(3)
    k = 12
    x = np.concatenate((rng.uniform(0, 6, k - 2), rng.uniform(-8, 8, k)))
    f0, g = objective(x, k, rollout, 1e-6)
    fd = np.zeros_like(x)
    for i in range(len(x)):
        xp = x.copy(); xp[i] += 1e-7
        fd[i] = (objective(xp, k, rollout, 1e-6)[0] - f0) / 1e-7
    return float(np.max(np.abs(fd - g)) / max(1e-12, np.max(np.abs(fd))))


def solve(graph: str, t_ns: int, lam=1e-5, seed=0):
    hx, hd, hint, mis_idx, n = build_operators(graph)
    rollout = make_rollout(hx, hd, hint, mis_idx)
    k = t_ns // DT_NS
    # Warm start: the deck baseline resampled to the knot grid.
    amp_b, det_b = score02.baseline_waveforms()
    tb = np.linspace(0, 1, len(amp_b))
    tk = np.linspace(0, 1, k)
    om0 = np.interp(tk, tb, amp_b)[1:-1]
    de0 = np.interp(tk, tb, det_b)
    rng = np.random.default_rng(seed)
    best = None
    for trial in range(3):
        o = np.clip(om0 * (1 + 0.1 * rng.standard_normal(k - 2) * (trial > 0)), 0, OMEGA_MAX)
        d = np.clip(de0 + 2.0 * rng.standard_normal(k) * (trial > 0), -DELTA_MAX, DELTA_MAX)
        x0 = np.concatenate((o, d))
        bounds = [(0, OMEGA_MAX)] * (k - 2) + [(-DELTA_MAX, DELTA_MAX)] * k
        res = minimize(objective, x0, args=(k, rollout, lam), jac=True,
                       method="L-BFGS-B", bounds=bounds,
                       options=dict(maxiter=1500, maxfun=80000))
        if best is None or res.fun < best.fun:
            best = res
    omega = np.concatenate(([0.0], best.x[:k - 2], [0.0]))
    delta = best.x[k - 2:]
    internal = 1.0 - rollout(omega, delta)[0]
    # Judge-facing cross-validation (rule: one scorer).
    amp = np.repeat(omega, DT_NS)
    det = np.repeat(delta, DT_NS)
    pulser_val, diag = score02.p_mis(amp, det, graph)
    return dict(graph=graph, T_ns=t_ns, internal=internal,
                pulser=pulser_val, diag=diag, omega=omega, delta=delta)


def main():
    hx, hd, hint, mis_idx, _ = build_operators("star_K13")
    err = verify_gradient(make_rollout(hx, hd, hint, mis_idx))
    print(f"gradient check (FD vs adjoint, star): {err:.2e}")
    assert err < 1e-4, "gradient wrong — refusing to optimize"

    out = {}
    for graph in ("star_K13", "cycle_C5"):
        for t_ns in (1000, 2000, 4000):
            r = solve(graph, t_ns)
            key = f"{graph}_T{t_ns}"
            out[key] = {k: (v if not isinstance(v, np.ndarray) else None)
                        for k, v in r.items() if k != "diag"}
            np.savez(f"opt_{key}.npz", omega=r["omega"], delta=r["delta"])
            print(f"{graph} T={t_ns}: internal={r['internal']:.6f}  "
                  f"PULSER P_MIS={r['pulser']:.6f}  "
                  f"per-MIS={ {k: round(v, 4) for k, v in r['diag']['per_mis'].items()} }")
    json.dump(out, open("opt02_results.json", "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
