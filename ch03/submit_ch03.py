#!/usr/bin/env python3
"""Ch03 validation runs — cloud at the paper's shot count, plus one real-QPU
point on a lattice-native instance.

  cloud:  N=11 and N=13 DUGG instances, our transferred sweep, EMU_FREE,
          500 shots each -> sampled r at matched shot count.
  qpu:    N=10 triangular-lattice instance (FRESNEL_CAN1's calibrated
          layout; a DUGG cannot be embedded there — stated openly),
          our sweep, 500 shots.

Usage: submit_ch03.py cloud | qpu | poll
"""

import json
import sys

import numpy as np
import pulser

sys.path.insert(0, "../ch01")
from pasqal_client import connect  # noqa: E402
from pasqal_cloud.device import DeviceTypeName, EmulatorType  # noqa: E402

import score03 as s3  # noqa: E402

RUNS = 500


def sampled_r(counts, coords, edges, alpha):
    edge_set = {tuple(sorted(e)) for e in edges}
    adj = {i: set() for i in range(len(coords))}
    for i, j in edges:
        adj[i].add(j); adj[j].add(i)
    tot = sum(counts.values())
    valid = valid_sz = rep_sz = mis = 0
    for b, c in counts.items():
        s = [i for i, ch in enumerate(b) if ch == "1"]
        ok = not any(tuple(sorted(p)) in edge_set
                     for p in __import__("itertools").combinations(s, 2))
        if ok:
            valid += c; valid_sz += c * len(s)
            if len(s) == alpha:
                mis += c
            rep_sz += c * len(s)
        else:
            rep_sz += c * len(s3.greedy_repair([1 if i in s else 0
                                                for i in range(len(coords))], adj))
    return dict(shots=tot, valid_fraction=valid / tot,
                r_valid=(valid_sz / valid / alpha) if valid else 0.0,
                r_repair=rep_sz / tot / alpha, P_MIS=mis / tot)


def build_seq(coords, params, reg=None, device=None):
    amp_k, det_k = s3.crab_knots(params, 2000)
    amp = np.repeat(amp_k, s3.DT_NS)
    det = np.repeat(det_k, s3.DT_NS)
    if reg is None:
        reg = pulser.Register.from_coordinates(coords, prefix="q", center=False)
        device = pulser.AnalogDevice
    seq = pulser.Sequence(reg, device)
    seq.declare_channel("rydberg_global", "rydberg_global")
    seq.add(pulser.Pulse(pulser.CustomWaveform(amp),
                         pulser.CustomWaveform(det), phase=0.0), "rydberg_global")
    seq.measure()
    return seq


def triangular_instance(layout, n_target=10, seed=4):
    """Connected random subset of the calibrated triangular lattice."""
    rng = np.random.default_rng(seed)
    coords = layout.coords - layout.coords.mean(0)
    # grow a random connected cluster of traps
    start = int(np.argmin(np.linalg.norm(coords, axis=1)))
    chosen = [start]
    while len(chosen) < n_target:
        frontier = set()
        for c in chosen:
            d = np.linalg.norm(coords - coords[c], axis=1)
            frontier.update(int(i) for i in np.where((d > 1) & (d < 5.1))[0])
        frontier -= set(chosen)
        chosen.append(int(rng.choice(sorted(frontier))))
    pos = [tuple(coords[i]) for i in chosen]
    edges = [(a, b) for a in range(n_target) for b in range(a + 1, n_target)
             if np.hypot(pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]) < s3.RB]
    return chosen, pos, edges


def main():
    mode = sys.argv[1]
    sdk = connect()
    res = json.load(open("ch03_results.json"))
    params = res["crab_params"]
    inst = json.load(open("instances.json"))

    if mode == "cloud":
        out = {}
        for n_str in ("11", "13"):
            d = inst[n_str]
            seq = build_seq([tuple(c) for c in d["coords"]], params)
            batch = sdk.create_batch(serialized_sequence=seq.to_abstract_repr(),
                                     jobs=[{"runs": RUNS}],
                                     emulator=EmulatorType.EMU_FREE, wait=True)
            counts = list(batch.ordered_jobs)[0].result or {}
            m = sampled_r(counts, d["coords"], [tuple(e) for e in d["edges"]],
                          d["alpha"])
            out[f"N{n_str}"] = dict(batch_id=batch.id, **m)
            print(f"CLOUD N={n_str}: r_valid={m['r_valid']:.4f} "
                  f"r_repair={m['r_repair']:.4f} valid={m['valid_fraction']:.3f}")
        json.dump(out, open("cloud_results_ch03.json", "w"), indent=1)

    elif mode == "qpu":
        spec = sdk.get_device_specs_dict()["FRESNEL_CAN1"]
        device = pulser.devices.Device.from_abstract_repr(spec)
        layout = min(device.pre_calibrated_layouts, key=lambda l: l.number_of_traps)
        ids, pos, edges = triangular_instance(layout)
        alpha = s3.alpha_of(len(pos), edges)
        reg = layout.define_register(*ids, qubit_ids=[f"q{k}" for k in range(len(ids))])
        seq = build_seq(pos, params, reg=reg, device=device)
        batch = sdk.create_batch(serialized_sequence=seq.to_abstract_repr(),
                                 jobs=[{"runs": RUNS}],
                                 device_type=DeviceTypeName.FRESNEL_CAN1, wait=False)
        json.dump(dict(batch_id=batch.id, coords=pos, edges=edges, alpha=alpha,
                       n=len(pos), params=params),
                  open("qpu_ch03_batch.json", "w"), indent=1)
        print(f"QPU N={len(pos)} triangular instance (alpha={alpha}, "
              f"{len(edges)} edges): batch={batch.id}")

    elif mode == "poll":
        ref = json.load(open("qpu_ch03_batch.json"))
        b = sdk.get_batch(ref["batch_id"])
        jobs = list(b.ordered_jobs)
        st = jobs[0].status if jobs else b.status
        print(f"qpu ch03: {st}")
        if st == "DONE":
            counts = jobs[0].result or {}
            m = sampled_r(counts, ref["coords"],
                          [tuple(e) for e in ref["edges"]], ref["alpha"])
            json.dump({**ref, "counts": dict(counts), **m},
                      open("qpu_ch03_results.json", "w"), indent=1)
            print(f"QPU measured: r_valid={m['r_valid']:.4f} "
                  f"r_repair={m['r_repair']:.4f} valid={m['valid_fraction']:.3f} "
                  f"P_MIS={m['P_MIS']:.3f}")


if __name__ == "__main__":
    main()
