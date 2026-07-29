#!/usr/bin/env python3
"""Challenge 03 scorer — approximation ratio r on random unit-disk instances.

Instance class (matching arXiv:2511.22967): DUGGs — square grid, spacing
5.0 um, random dropout; edges between pairs closer than R_b = 7.19 um, so
nearest neighbours (5.0) AND diagonals (7.07) are edges, next-nearest
(10.0) are not. Device floor allows 5.0 um exactly.

Metric (the paper's, with C_worst = 0, valid solutions only):
    r = E[ |S| : S independent ] / alpha(G),  plus the valid fraction.
We also report r_repair: every measured bitstring greedily repaired to an
independent set (standard post-processing) then averaged — the practical
solver metric.

Simulation: sparse Krylov propagation (expm_multiply), exact for N <= 17.
"""

import itertools
import json

import numpy as np
from scipy.sparse import csr_matrix, diags
from scipy.sparse.linalg import expm_multiply

C6 = 865723.02
OMEGA_B = 2 * np.pi * 1.0
RB = (C6 / OMEGA_B) ** (1 / 6)
DT_NS = 8
DT_US = DT_NS / 1000.0
A_GRID = 5.0


def make_dugg(n_target, shape, seed):
    """Random-dropout square-grid instance with exactly n_target atoms."""
    rng = np.random.default_rng(seed)
    w, h = shape
    sites = [(A_GRID * x, A_GRID * y) for x in range(w) for y in range(h)]
    while True:
        keep = rng.choice(len(sites), size=n_target, replace=False)
        coords = [sites[k] for k in sorted(keep)]
        edges = [(i, j) for i in range(n_target) for j in range(i + 1, n_target)
                 if np.hypot(coords[i][0] - coords[j][0],
                             coords[i][1] - coords[j][1]) < RB]
        # require connectivity (paper instances are connected)
        adj = {i: set() for i in range(n_target)}
        for i, j in edges:
            adj[i].add(j); adj[j].add(i)
        seen, stack = {0}, [0]
        while stack:
            for k in adj[stack.pop()]:
                if k not in seen:
                    seen.add(k); stack.append(k)
        if len(seen) == n_target:
            return coords, edges


def alpha_of(n, edges):
    edge_set = {tuple(sorted(e)) for e in edges}
    for size in range(n, 0, -1):
        for subset in itertools.combinations(range(n), size):
            if not any(tuple(sorted(p)) in edge_set
                       for p in itertools.combinations(subset, 2)):
                return size
    return 0


def operators(coords, edges):
    n = len(coords)
    dim = 2 ** n
    hd = np.zeros(dim)
    hint = np.zeros(dim)
    rows, cols = [], []
    umat = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            umat[i, j] = C6 / np.hypot(coords[i][0] - coords[j][0],
                                       coords[i][1] - coords[j][1]) ** 6
    for state in range(dim):
        bits = [(state >> (n - 1 - q)) & 1 for q in range(n)]
        hd[state] = -sum(bits)
        e = 0.0
        for i in range(n):
            if bits[i]:
                for j in range(i + 1, n):
                    if bits[j]:
                        e += umat[i, j]
        hint[state] = e
        for q in range(n):
            rows.append(state ^ (1 << (n - 1 - q)))
            cols.append(state)
    hx = csr_matrix((np.full(len(rows), 0.5), (rows, cols)), shape=(dim, dim))
    return hx, hd, hint


def propagate(amp_knots, det_knots, hx, hd, hint):
    dim = hx.shape[0]
    psi = np.zeros(dim, complex)
    psi[0] = 1.0
    for om, de in zip(amp_knots, det_knots):
        h = (om * hx + diags(de * hd + hint)).tocsr()
        psi = expm_multiply(-1j * DT_US * h, psi)
    return psi


def greedy_repair(bits, adj):
    s = set(i for i, b in enumerate(bits) if b)
    while True:
        viol = [(i, j) for i in s for j in adj[i] if j in s and i < j]
        if not viol:
            return s
        deg = {}
        for i, j in viol:
            deg[i] = deg.get(i, 0) + 1
            deg[j] = deg.get(j, 0) + 1
        s.discard(max(deg, key=deg.get))


def metrics(psi, n, edges, alpha):
    """Exact expected metrics from the state vector (no sampling noise)."""
    edge_set = {tuple(sorted(e)) for e in edges}
    adj = {i: set() for i in range(n)}
    for i, j in edges:
        adj[i].add(j); adj[j].add(i)
    probs = np.abs(np.asarray(psi).ravel()) ** 2
    p_valid = mis_p = r_valid_num = r_rep = 0.0
    for idx, p in enumerate(probs):
        if p < 1e-12:
            continue
        bits = [((2 ** n - 1 - idx) >> (n - 1 - q)) & 1 for q in range(n)]
        s = [i for i, b in enumerate(bits) if b]
        indep = not any(tuple(sorted(pr)) in edge_set
                        for pr in itertools.combinations(s, 2))
        if indep:
            p_valid += p
            r_valid_num += p * len(s)
            if len(s) == alpha:
                mis_p += p
            r_rep += p * len(s)
        else:
            r_rep += p * len(greedy_repair(bits, adj))
    return dict(P_MIS=mis_p, valid_fraction=p_valid,
                r_valid=(r_valid_num / p_valid / alpha) if p_valid else 0.0,
                r_repair=r_rep / alpha)


def baseline_knots(t_ns=6000):
    """The deck's ch03 starter: the ch02 ramp stretched to 6000 ns."""
    k = t_ns // DT_NS
    tt = (np.arange(k) + 0.5) / k
    rise = 252 / t_ns
    amp = np.full(k, OMEGA_B)
    amp[tt < rise] = OMEGA_B * tt[tt < rise] / rise
    amp[tt > 1 - rise] = OMEGA_B * (1 - tt[tt > 1 - rise]) / rise
    det = -2 * np.pi * 2.0 + (4 * np.pi * 2.0) * tt
    return amp, det


def crab_knots(params, t_ns):
    a, d0, df, c1, c2 = params
    k = t_ns // DT_NS
    s = (np.arange(k) + 0.5) / k
    amp = a * np.sin(np.pi * s) ** 2
    det = d0 + (df - d0) * s + c1 * np.sin(np.pi * s) + c2 * np.sin(2 * np.pi * s)
    return amp, det


if __name__ == "__main__":
    inst = {}
    for n, shape, seed in [(11, (4, 4), 3), (13, (4, 5), 7), (17, (5, 5), 5)]:
        coords, edges = make_dugg(n, shape, seed)
        alpha = alpha_of(n, edges)
        inst[str(n)] = dict(coords=coords, edges=edges, alpha=alpha)
        print(f"N={n}: {len(edges)} edges, alpha={alpha}")
    json.dump(inst, open("instances.json", "w"))
    print(f"R_b = {RB:.3f} um; U(5.0) = {C6/5.0**6:.2f}, U(7.07) = "
          f"{C6/(5*2**0.5)**6:.2f}, U(10.0) = {C6/10.0**6:.2f} rad/us")
    print("NOTE: the deck-baseline final detuning 12.57 rad/us EXCEEDS the"
          " weakest-edge penalty U(7.07) = 6.94 — the starter's ground state"
          " can violate diagonal edges. Our window: d_f in (0.87, 6.94).")
