#!/usr/bin/env python3
"""Poll the FRESNEL QPU batch; on completion, record measured populations."""

import json
import sys

from pasqal_client import connect


def main() -> None:
    ref = json.load(open("qpu_batch.json"))
    sdk = connect()
    batch = sdk.get_batch(ref["batch_id"])
    jobs = list(batch.ordered_jobs)
    status = jobs[0].status if jobs else batch.status
    print(f"batch {ref['batch_id']}: {status}")
    if status not in ("DONE", "ERROR", "CANCELED"):
        sys.exit(2)                      # still queued/running
    if status != "DONE":
        sys.exit(f"terminal non-success: {status}")

    counts = jobs[0].result or {}
    total = sum(counts.values()) or 1
    pops = {
        "P_gg": counts.get("00", 0) / total,
        "P_gr": counts.get("01", 0) / total,
        "P_rg": counts.get("10", 0) / total,
        "P_rr": counts.get("11", 0) / total,
    }
    out = {**ref, "status": "DONE", "counts": dict(counts), "pops": pops,
           "P_bell": pops["P_gr"] + pops["P_rg"]}
    json.dump(out, open("qpu_results.json", "w"), indent=1)
    print(f"counts: {dict(counts)}")
    print(f"pops:   { {k: round(v, 4) for k, v in pops.items()} }")
    print(f"P_bell (target manifold): {out['P_bell']:.4f}")
    print("wrote qpu_results.json")


if __name__ == "__main__":
    main()
