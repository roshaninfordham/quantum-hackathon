#!/usr/bin/env python3
"""Submit the hardware-true v3 pulse to the FRESNEL QPU (real atoms).

Differences from the emulator path (submit_ch01.py):
  - Device: FRESNEL spec fetched live from the cloud (not AnalogDevice) —
    tighter Omega/detuning bounds, modulation bandwidth 8 MHz, and
    requires_layout: the register MUST come from the pre-calibrated
    TriangularLatticeLayout(120, 5.0um). Two traps 5.0 um apart are chosen
    near the layout centre.
  - Submitted with wait=False: QPU queues are minutes-to-hours; we record
    the batch id and poll separately (poll_qpu.py).

Spends real hardware budget — run only after an explicit human go.
"""

import json
import sys

import numpy as np
import pulser
from pasqal_cloud.device import DeviceTypeName

from pasqal_client import connect

RUNS = 500
NPZ = "v3_r5.0_T260.npz"


def main() -> None:
    sdk = connect()
    # FRESNEL's 120-trap layout enforces >= 42 qubits (min filling fraction);
    # FRESNEL_CAN1 carries the minimum-size 60-trap layout, which pulser
    # exempts for arbitrarily small registers — the only QPU path for 2 atoms.
    spec = sdk.get_device_specs_dict()["FRESNEL_CAN1"]
    device = pulser.devices.Device.from_abstract_repr(spec)
    layout = min(device.pre_calibrated_layouts, key=lambda l: l.number_of_traps)

    # Two traps exactly 5.0 um apart, nearest the layout centre (trap ids
    # found by search over the calibrated layout; re-derived here so a
    # layout update cannot silently invalidate them).
    coords = layout.coords - layout.coords.mean(0)
    best = None
    for i in range(len(coords)):
        for j in range(i + 1, len(coords)):
            d = float(np.linalg.norm(coords[i] - coords[j]))
            if abs(d - 5.0) < 1e-6:
                centre = float(np.linalg.norm((coords[i] + coords[j]) / 2))
                if best is None or centre < best[0]:
                    best = (centre, i, j)
    _, i, j = best
    register = layout.define_register(i, j, qubit_ids=["q0", "q1"])

    d = np.load(NPZ)
    amp = np.repeat(d["omega"], 4)
    det = np.repeat(d["delta"], 4)
    # FRESNEL envelope check happens inside Sequence construction (pulser
    # validates against the device) — a violation raises before submission.
    seq = pulser.Sequence(register, device)
    seq.declare_channel("rydberg_global", "rydberg_global")
    seq.add(pulser.Pulse(pulser.CustomWaveform(amp), pulser.CustomWaveform(det), phase=0.0),
            "rydberg_global")
    seq.measure()
    print(f"sequence valid on {device.name}: duration {seq.get_duration()} ns, "
          f"traps ({i},{j})", flush=True)

    batch = sdk.create_batch(
        serialized_sequence=seq.to_abstract_repr(),
        jobs=[{"runs": RUNS}],
        device_type=DeviceTypeName.FRESNEL_CAN1,
        wait=False,
    )
    record = {"batch_id": batch.id, "device": "FRESNEL_CAN1", "pulse": NPZ,
              "runs": RUNS, "status": batch.status}
    json.dump(record, open("qpu_batch.json", "w"), indent=1)
    print(f"QPU batch submitted: id={batch.id} status={batch.status}")
    print("poll with: .venv/bin/python ch01/poll_qpu.py")


if __name__ == "__main__":
    main()
