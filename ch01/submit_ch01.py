#!/usr/bin/env python3
"""Submit Challenge-01 pulses to Pasqal Cloud and record measured populations.

Token-only auth via pasqal_client. Submits each pulse.toml as its own batch
(one sequence per batch), waits, and writes cloud_results.json mapping
pulse name -> bitstring counts + derived populations.

Usage:
    submit_ch01.py EMU_FREE pulse_r1 pulse_r2 ...
    submit_ch01.py FRESNEL ...      # real QPU — only run after explicit OK

Bitstring convention (pulser ground-rydberg): '1' = atom measured in |r>,
string ordered by register qubit ids (q0 = left atom, q1 = right atom).
So P_gr (left ground, right rydberg) is counts['01']/runs.
"""

import json
import sys
import tomllib

import numpy as np
import pulser
from pasqal_cloud.device import EmulatorType

import score
from pasqal_client import connect

RUNS = 500


def sequence_from_toml(path: str) -> tuple[pulser.Sequence, dict]:
    with open(path, "rb") as f:
        data = tomllib.load(f)
    amp = np.repeat(data["amplitude"][:-1], int(data["dt_ns"]))
    det = np.repeat(data["detuning"][:-1], int(data["dt_ns"]))
    atoms = data["atoms"]
    r_um = float(np.hypot(atoms[1][0] - atoms[0][0], atoms[1][1] - atoms[0][1]))
    seq = score.build_sequence(amp, det, r_um)
    seq.measure()
    return seq, data


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit(f"usage: {sys.argv[0]} <EMU_FREE|EMU_TN|FRESNEL> <pulse-name>...")
    target = sys.argv[1]
    names = sys.argv[2:]

    sdk = connect()
    kwargs: dict = {}
    if target.startswith("EMU_"):
        kwargs["emulator"] = EmulatorType(target)
    else:
        # A real-QPU submission spends the team's hardware budget; the caller
        # gates this behind an explicit human OK, not this script.
        from pasqal_cloud.device import DeviceTypeName
        kwargs["device_type"] = DeviceTypeName(target)

    results = {}
    for name in names:
        seq, data = sequence_from_toml(f"{name}.toml")
        print(f"[{name}] submitting to {target} ({RUNS} runs, "
              f"sim F={data.get('fidelity'):.6f}) ...", flush=True)
        batch = sdk.create_batch(
            serialized_sequence=seq.to_abstract_repr(),
            jobs=[{"runs": RUNS}],
            wait=True,
            **kwargs,
        )
        job = list(batch.ordered_jobs)[0]
        counts = job.result or {}
        total = sum(counts.values()) or 1
        pops = {
            "P_gg": counts.get("00", 0) / total,
            "P_gr": counts.get("01", 0) / total,
            "P_rg": counts.get("10", 0) / total,
            "P_rr": counts.get("11", 0) / total,
        }
        results[name] = {
            "target": target,
            "batch_id": batch.id,
            "job_status": job.status,
            "counts": counts,
            "pops": pops,
            "sim_fidelity": data.get("fidelity"),
        }
        print(f"[{name}] status={job.status} counts={dict(counts)}")
        print(f"[{name}] pops={ {k: round(v, 4) for k, v in pops.items()} }", flush=True)

    out = f"cloud_results_{target}.json"
    json.dump(results, open(out, "w"), indent=1)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
