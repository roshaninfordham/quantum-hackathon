#!/usr/bin/env python3
"""Low-bandwidth (CRAB-style) MIS sweeps + the transfer experiment.

The scientists' requirements, made precise:

1. LOW BANDWIDTH. Replace the ~250-knot GRAPE waveform with a
   physically-parameterized family (Chopped RAndom Basis, Caneva/Calarco/
   Montangero PRA 84, 022326 (2011)):
       Omega(t) = A * sin^2(pi t / T)
       delta(t) = d0 + (df - d0) * t/T + sum_k c_k sin(k pi t / T)
   K modes on top of a linear ramp -> 3 + K parameters total, spectral
   content bounded by k_max/(2T) BY CONSTRUCTION (a hard bandwidth
   certificate, not an after-the-fact FFT claim).

2. LEAST COMPUTE. Derivative-free Nelder-Mead over <= 6 parameters against
   the exact propagator: hundreds of evaluations, seconds of laptop time.
   Every run logs its evaluation count and wall time (the compute ledger).

3. SCALE / TRANSFER. The parameters optimized on C_5 are applied UNCHANGED
   to larger rings (C_7, C_9) and a random 10-atom unit-disk instance,
   against the deck baseline on the same graphs. Zero re-optimization =
   compute cost independent of N. Larger registers are propagated with
   sparse Krylov stepping (expm_multiply), not dense eigh.

All small-graph winners are cross-scored through ch02/score02.py (Pulser).
"""

import itertools
import json
import time

import numpy as np
from scipy.optimize import minimize
from scipy.sparse import csr_matrix, diags
from scipy.sparse.linalg import expm_multiply

import opt02
import score02

DT_NS = 8
DT_US = DT_NS / 1000.0
OMEGA_MAX = score02.DEVICE.channels[score02.CHANNEL].max_amp
C6 = score02.DEVICE.interaction_coeff
RB = (C6 / score02.OMEGA_B) ** (1 / 6)


# ── waveform family ──────────────────────────────────────────────────────
def waveforms(params, t_ns):
    """params = [A, d0, df, c_1..c_K] -> (omega, delta) on the 8 ns grid."""
    a, d0, df = params[:3]
    cs = params[3:]
    k = t_ns // DT_NS
    s = (np.arange(k) + 0.5) / k
    omega = a * np.sin(np.pi * s) ** 2
    delta = d0 + (df - d0) * s
    for i, c in enumerate(cs, start=1):
        delta = delta + c * np.sin(i * np.pi * s)
    return omega, delta


# ── generic graph -> operators (any register) ────────────────────────────
def graph_operators(coords, edges):
    coords = [np.asarray(c, float) for c in coords]
    n = len(coords)
    dim = 2 ** n
    rows, cols = [], []
    hd = np.zeros(dim)
    hint = np.zeros(dim)
    for state in range(dim):
        bits = [(state >> (n - 1 - q)) & 1 for q in range(n)]
        hd[state] = -sum(bits)
        for i in range(n):
            for j in range(i + 1, n):
                if bits[i] and bits[j]:
                    hint[state] += C6 / np.linalg.norm(coords[i] - coords[j]) ** 6
        for q in range(n):
            rows.append(state ^ (1 << (n - 1 - q)))
            cols.append(state)
    hx = csr_matrix((np.full(len(rows), 0.5), (rows, cols)), shape=(dim, dim))
    return hx, hd, hint, n


def alpha_and_mis(n, edges):
    """Brute-force alpha(G) and the MIS state indices (bit=1 -> |r>)."""
    edge_set = {tuple(sorted(e)) for e in edges}
    best, idxs = 0, []
    for size in range(n, 0, -1):
        found = []
        for subset in itertools.combinations(range(n), size):
            if not any(tuple(sorted(p)) in edge_set
                       for p in itertools.combinations(subset, 2)):
                found.append(sum(1 << (n - 1 - q) for q in subset))
        if found:
            return size, found
    return 0, [2 ** n - 1]


def p_mis_sparse(params_or_wf, coords, edges, t_ns, is_params=True):
    """P_MIS via sparse Krylov propagation (any N)."""
    hx, hd, hint, n = graph_operators(coords, edges)
    alpha, idxs = alpha_and_mis(n, edges)
    omega, delta = waveforms(params_or_wf, t_ns) if is_params else params_or_wf
    psi = np.zeros(2 ** n, complex)
    psi[0] = 1.0
    for om, de in zip(omega, delta):
        h = (om * hx + diags(de * hd + hint)).tocsr()
        psi = expm_multiply(-1j * DT_US * h, psi)
    return float(np.sum(np.abs(psi[idxs]) ** 2)), alpha


# ── optimization on the deck graphs (dense fast path via opt02) ──────────
def optimize(graph, t_ns, n_modes, seed=0):
    hx, hd, hint, mis_idx, _ = opt02.build_operators(graph)
    rollout = opt02.make_rollout(hx, hd, hint, mis_idx)
    evals = [0]

    def neg(params):
        evals[0] += 1
        if not (0 < params[0] <= OMEGA_MAX):
            return 1.0
        omega, delta = waveforms(params, t_ns)
        if np.abs(delta).max() > score02.DEVICE.channels[score02.CHANNEL].max_abs_detuning:
            return 1.0
        return rollout(omega, delta)[0]

    rng = np.random.default_rng(seed)
    x0 = np.array([score02.OMEGA_B, score02.DELTA_0, score02.DELTA_F]
                  + [0.0] * n_modes)
    best = None
    t0 = time.time()
    for trial in range(4):
        x = x0 * (1 + 0.15 * rng.standard_normal(len(x0)) * (trial > 0))
        x[3:] += 3.0 * rng.standard_normal(n_modes) * (trial > 0)
        res = minimize(neg, x, method="Nelder-Mead",
                       options=dict(maxfev=600, xatol=1e-4, fatol=1e-9))
        if best is None or res.fun < best.fun:
            best = res
    wall = time.time() - t0
    omega, delta = waveforms(best.x, t_ns)
    pulser_val, _ = score02.p_mis(np.repeat(omega, DT_NS), np.repeat(delta, DT_NS), graph)
    return dict(params=[float(v) for v in best.x], n_params=3 + n_modes,
                internal=1 - float(best.fun), pulser=pulser_val,
                evals=evals[0], wall_s=round(wall, 2),
                bandwidth_MHz=round((n_modes or 1) / (2 * t_ns * 1e-3), 3))


# ── transfer registers ───────────────────────────────────────────────────
def ring(n_atoms, side=5.5):
    rad = side / (2 * np.sin(np.pi / n_atoms))
    coords = [(rad * np.cos(2 * np.pi * k / n_atoms),
               rad * np.sin(2 * np.pi * k / n_atoms)) for k in range(n_atoms)]
    edges = [(k, (k + 1) % n_atoms) for k in range(n_atoms)]
    return coords, edges


def random_ud(n_atoms=10, seed=11):
    """Random unit-disk instance: min spacing 5.2 um, edges iff < R_b."""
    rng = np.random.default_rng(seed)
    pts = []
    while len(pts) < n_atoms:
        p = rng.uniform(-14, 14, 2)
        if all(np.linalg.norm(p - q) >= 5.2 for q in pts):
            pts.append(p)
    edges = [(i, j) for i in range(n_atoms) for j in range(i + 1, n_atoms)
             if np.linalg.norm(pts[i] - pts[j]) < RB]
    return [tuple(p) for p in pts], edges


def main():
    t_ns = 1000
    results = {"optimize": {}, "mode_sweep": {}, "transfer": {}}

    # 1+2: low-bandwidth optimization + parameter-count sweep
    for graph in ("star_K13", "cycle_C5"):
        for n_modes in (0, 1, 2, 3):
            r = optimize(graph, t_ns, n_modes)
            results["mode_sweep"][f"{graph}_K{n_modes}"] = r
            print(f"{graph} K={n_modes} ({r['n_params']} params, BW<={r['bandwidth_MHz']} MHz): "
                  f"P_MIS={r['pulser']:.6f}  [{r['evals']} evals, {r['wall_s']}s]")
        results["optimize"][graph] = results["mode_sweep"][f"{graph}_K3"]

    # 3: transfer — C5's K=3 params, UNCHANGED, on bigger graphs
    params = results["optimize"]["cycle_C5"]["params"]
    amp_b, det_b = score02.baseline_waveforms()
    base_wf = (amp_b[::DT_NS], det_b[::DT_NS])          # deck ramp, resampled
    for name, (coords, edges) in {
        "cycle_C7": ring(7), "cycle_C9": ring(9), "random_UD_N10": random_ud(),
    }.items():
        t0 = time.time()
        p_ours, alpha = p_mis_sparse(params, coords, edges, t_ns)
        p_base, _ = p_mis_sparse(base_wf, coords, edges, len(amp_b), is_params=False)
        results["transfer"][name] = dict(
            n=len(coords), alpha=alpha, n_edges=len(edges),
            P_ours_transferred=p_ours, P_baseline=p_base,
            wall_s=round(time.time() - t0, 1))
        print(f"TRANSFER {name} (N={len(coords)}, alpha={alpha}): "
              f"ours={p_ours:.4f} vs baseline={p_base:.4f}  "
              f"[{results['transfer'][name]['wall_s']}s, zero re-optimization]")

    json.dump(results, open("crab02_results.json", "w"), indent=1)
    np.savez("crab_cycle_C5_T1000.npz",
             omega=waveforms(params, t_ns)[0], delta=waveforms(params, t_ns)[1])
    p = results["optimize"]["star_K13"]["params"]
    np.savez("crab_star_K13_T1000.npz",
             omega=waveforms(p, t_ns)[0], delta=waveforms(p, t_ns)[1])
    print("wrote crab02_results.json + crab_*.npz")


if __name__ == "__main__":
    main()
