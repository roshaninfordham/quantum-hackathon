#!/usr/bin/env python3
"""Challenge 02 on real atoms: star K_{1,3} MIS on FRESNEL_CAN1.

Self-instruction (experiment protocol, docs/ch01/08-prompts.md):
  HYPOTHESIS: a 5-parameter CRAB sweep re-optimized for the lattice-native
    star (rho = 5.0 um) returns the unique MIS |0111> on the real QPU with
    P_MIS above the deck baseline's NOISELESS value 0.727 — i.e. real
    hardware beats the idealized baseline.
  PREDICTION (pre-registered): sim P_MIS >= 0.99; measured 0.80-0.93 after
    noise + SPAM (scaling ch01's measured QPU degradation, 1.000 -> 0.894,
    to a 4-atom register and 1000 ns).
  DESIGN: register = 4 traps of the calibrated 60-trap triangular layout
    (center + 3 alternating nearest neighbors: edges 5.0 < R_b = 7.19 um,
    non-edges 8.66 > R_b -> exactly K_{1,3}); sweep bandwidth <= 1 MHz
    (inside CAN1's 5 MHz modulation bandwidth by construction);
    500 shots; measured P_MIS = fraction of shots reading 0111.
  RUN/STATS/VERDICT: recorded in ch02/qpu_star_results.json + docs.
"""

import json
import sys

import numpy as np
import pulser
from scipy.optimize import minimize

import crab02
import score02

sys.path.insert(0, "../ch01")
from pasqal_client import connect  # noqa: E402
from pasqal_cloud.device import DeviceTypeName  # noqa: E402

T_NS = 1000
RUNS = 500


def lattice_star(device):
    """Center trap + 3 alternating nearest neighbors from the layout."""
    layout = min(device.pre_calibrated_layouts, key=lambda l: l.number_of_traps)
    coords = layout.coords
    center = int(np.argmin(np.linalg.norm(coords - coords.mean(0), axis=1)))
    d = np.linalg.norm(coords - coords[center], axis=1)
    nn = [i for i in np.argsort(d)[1:10] if abs(d[i] - 5.0) < 1e-6]
    ang = np.arctan2(*(coords[nn] - coords[center]).T[::-1])
    order = np.argsort(ang)
    leaves = [nn[order[0]], nn[order[2]], nn[order[4]]]     # alternating 120 deg
    ids = [center] + leaves
    reg = layout.define_register(*ids, qubit_ids=[f"q{k}" for k in range(4)])
    pos = [coords[i] for i in ids]
    for a, b, lo, hi in [(0, 1, 4.9, 5.1), (1, 2, 8.5, 8.8)]:
        dd = np.linalg.norm(np.array(pos[a]) - np.array(pos[b]))
        assert lo < dd < hi, f"geometry check failed: d({a},{b})={dd:.3f}"
    return reg, pos


def main():
    sdk = connect()
    spec = sdk.get_device_specs_dict()["FRESNEL_CAN1"]
    device = pulser.devices.Device.from_abstract_repr(spec)
    reg, pos = lattice_star(device)
    edges = [(0, 1), (0, 2), (0, 3)]

    # Re-optimize the 5-parameter sweep for THIS geometry (exact 16-dim).
    hx_s, hd, hint, n = crab02.graph_operators(pos, edges)
    alpha, mis_idx = crab02.alpha_and_mis(n, edges)
    hx = np.asarray(hx_s.todense())
    ch = device.channels["rydberg_global"]

    def neg(params):
        if not (0 < params[0] <= ch.max_amp):
            return 1.0
        om, de = crab02.waveforms(params, T_NS)
        if np.abs(de).max() > ch.max_abs_detuning:
            return 1.0
        psi = np.zeros(2 ** n, complex); psi[0] = 1.0
        for o, dd in zip(om, de):
            h = o * hx + np.diag(dd * hd + hint)
            lam, e = np.linalg.eigh(h)
            psi = e @ (np.exp(-1j * lam * crab02.DT_US) * (e.conj().T @ psi))
        return 1.0 - float(np.sum(np.abs(psi[mis_idx]) ** 2))

    best = None
    seed = json.load(open("crab_best.json"))["star_K13"]["params"]
    rng = np.random.default_rng(5)
    for trial in range(4):
        x0 = np.array(seed) * (1 + 0.1 * rng.standard_normal(len(seed)) * (trial > 0))
        res = minimize(neg, x0, method="Nelder-Mead",
                       options=dict(maxfev=800, xatol=1e-4, fatol=1e-9))
        if best is None or res.fun < best.fun:
            best = res
    sim_pmis = 1.0 - float(best.fun)
    om, de = crab02.waveforms(best.x, T_NS)
    print(f"lattice-star sweep: sim P_MIS = {sim_pmis:.6f} "
          f"(5 params, peak Omega {om.max():.2f} rad/us)")
    assert sim_pmis > 0.99, "below pre-registered floor — do not spend shots"

    amp, det = np.repeat(om, crab02.DT_NS), np.repeat(de, crab02.DT_NS)
    seq = pulser.Sequence(reg, device)
    seq.declare_channel("rydberg_global", "rydberg_global")
    seq.add(pulser.Pulse(pulser.CustomWaveform(amp), pulser.CustomWaveform(det),
                         phase=0.0), "rydberg_global")
    seq.measure()
    batch = sdk.create_batch(serialized_sequence=seq.to_abstract_repr(),
                             jobs=[{"runs": RUNS}],
                             device_type=DeviceTypeName.FRESNEL_CAN1, wait=False)
    json.dump(dict(batch_id=batch.id, device="FRESNEL_CAN1", graph="star_K13_lattice",
                   rho_um=5.0, sim_P_MIS=sim_pmis, params=[float(v) for v in best.x],
                   runs=RUNS, status=batch.status),
              open("qpu_star_batch.json", "w"), indent=1)
    np.savez("crab_star_lattice_T1000.npz", omega=om, delta=de)
    print(f"QPU batch submitted: {batch.id} status={batch.status}")


if __name__ == "__main__":
    main()
