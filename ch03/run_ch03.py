#!/usr/bin/env python3
"""Challenge 03 — optimize on N=11, transfer to N=13 and N=17, score vs
the deck baseline and the published pasqal_fresnel curve (arXiv:2511.22967:
r = 0.907 @ 11, 0.908 @ 13, 0.870 @ 17; QAA, 500 shots).

Objective: maximize r_repair (smooth in the state; equals the practical
solver metric). 5-knob CRAB family, T = 2000 ns, Nelder-Mead. The physics
head-start: the window analysis says delta_f must sit in (0.87, 6.94)
rad/us — the deck baseline's 12.57 is OUTSIDE it (violates diagonal edges).
"""

import json
import time

import numpy as np
from scipy.optimize import minimize

import score03 as s3

T_OPT = 2000
inst = json.load(open("instances.json"))
OPS = {}
for n_str, d in inst.items():
    OPS[n_str] = (s3.operators(d["coords"], d["edges"]), d)


def evaluate(params_or_baseline, n_str, t_ns=T_OPT):
    (hx, hd, hint), d = OPS[n_str]
    if params_or_baseline == "baseline":
        amp, det = s3.baseline_knots(6000)
    else:
        amp, det = s3.crab_knots(params_or_baseline, t_ns)
    psi = s3.propagate(amp, det, hx, hd, hint)
    return s3.metrics(psi, len(d["coords"]), [tuple(e) for e in d["edges"]],
                      d["alpha"])


def main():
    results = {"paper_fresnel_QAA": {"11": 0.907, "13": 0.908, "17": 0.870}}

    print("=== deck baseline (6000 ns ramp) ===")
    for n_str in ("11", "13", "17"):
        t0 = time.time()
        m = evaluate("baseline", n_str)
        results[f"baseline_N{n_str}"] = m
        print(f"N={n_str}: r_valid={m['r_valid']:.4f} r_repair={m['r_repair']:.4f} "
              f"P_MIS={m['P_MIS']:.4f} valid={m['valid_fraction']:.3f} "
              f"[{time.time()-t0:.0f}s]")

    print("=== optimize 5-knob CRAB on N=11 (r_repair objective) ===")
    evals = [0]

    def neg(p):
        evals[0] += 1
        if not (0 < p[0] <= 12.566):
            return 1.0
        return 1.0 - evaluate(list(p), "11")["r_repair"]

    rng = np.random.default_rng(2)
    x0 = np.array([2 * np.pi * 1.0, -12.57, 4.0, 0.0, 0.0])   # d_f INSIDE the window
    best = None
    t0 = time.time()
    for trial in range(3):
        x = x0 * (1 + 0.15 * rng.standard_normal(5) * (trial > 0))
        r = minimize(neg, x, method="Nelder-Mead",
                     options=dict(maxfev=250, xatol=1e-3, fatol=1e-6))
        if best is None or r.fun < best.fun:
            best = r
    params = [float(v) for v in best.x]
    print(f"trained on N=11: {evals[0]} evals, {time.time()-t0:.0f}s, "
          f"params={np.round(params, 3)}")
    results["crab_params"] = params

    print("=== our sweep: trained N=11, TRANSFERRED to 13 and 17 ===")
    for n_str in ("11", "13", "17"):
        t0 = time.time()
        m = evaluate(params, n_str)
        results[f"ours_N{n_str}"] = m
        tag = "trained" if n_str == "11" else "TRANSFERRED"
        print(f"N={n_str} ({tag}): r_valid={m['r_valid']:.4f} "
              f"r_repair={m['r_repair']:.4f} P_MIS={m['P_MIS']:.4f} "
              f"valid={m['valid_fraction']:.3f} [{time.time()-t0:.0f}s]")

    json.dump(results, open("ch03_results.json", "w"), indent=1)
    print("wrote ch03_results.json")


if __name__ == "__main__":
    main()
