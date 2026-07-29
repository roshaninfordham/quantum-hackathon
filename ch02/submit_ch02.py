#!/usr/bin/env python3
"""Submit ch02 optimized sweeps to Pasqal Cloud; record measured P_MIS.

Usage: submit_ch02.py EMU_FREE opt_star_K13_T1000 opt_cycle_C5_T1000 ...

Measured P_MIS = fraction of shots whose bitstring (1 = |r>) is an
independent set of size alpha — the challenge's own hardware metric.
"""

import json
import sys

import numpy as np
from pasqal_cloud.device import EmulatorType

import score02

sys.path.insert(0, "../ch01")
from pasqal_client import connect  # noqa: E402

RUNS = 500


def main() -> None:
    target = sys.argv[1]
    names = sys.argv[2:]
    sdk = connect()
    results = {}
    for name in names:
        graph = "star_K13" if "star" in name else "cycle_C5"
        reg, edges, alpha = score02.GRAPHS[graph]()
        n = len(reg.qubits)
        d = np.load(f"{name}.npz")
        amp = np.repeat(d["omega"], 8)
        det = np.repeat(d["delta"], 8)
        seq = score02.build_sequence(amp, det, reg)
        seq.measure()
        sim_val, _ = score02.p_mis(amp, det, graph)
        good = {score02.excitation_pattern(i, n)
                for i in score02.mis_bitstrings(n, edges, alpha)}
        print(f"[{name}] {graph} sim={sim_val:.6f} -> {target} ...", flush=True)
        batch = sdk.create_batch(
            serialized_sequence=seq.to_abstract_repr(),
            jobs=[{"runs": RUNS}], emulator=EmulatorType(target), wait=True)
        job = list(batch.ordered_jobs)[0]
        counts = job.result or {}
        total = sum(counts.values()) or 1
        hit = sum(v for k, v in counts.items() if k in good)
        results[name] = dict(graph=graph, batch_id=batch.id, counts=dict(counts),
                             P_MIS_measured=hit / total, P_MIS_sim=sim_val)
        print(f"[{name}] measured P_MIS = {hit / total:.4f} ({hit}/{total})  "
              f"counts={dict(sorted(counts.items(), key=lambda x: -x[1])[:6])}", flush=True)
    out = f"cloud_results_{target}.json"
    merged = {}
    try:
        merged = json.load(open(out))
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    merged.update(results)
    json.dump(merged, open(out, "w"), indent=1)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
