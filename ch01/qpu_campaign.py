#!/usr/bin/env python3
"""The closing QPU campaign — four experiments, pre-registered, 1500 shots.

Experiment protocol per docs/ch01/08-prompts.md. Predictions are computed
and written to qpu_campaign_predictions.json BEFORE submission.

  A. SPAM-idle (250 shots): two atoms 12.99 um apart (no blockade), zero
     pulse. Every '1' in the readout is a false-ON. Measures readout floor.
  B. SPAM-pi (250 shots): same register, independent smooth pi-pulse on
     each atom (V = 0.18 rad/us, negligible). Expect '11'; every '0' is a
     lost ON atom. Together with A this calibrates epsilon per atom.
  C. Coherence echo (500 shots): 5.0-um pair; the v3 260-ns Bell pulse
     applied TWICE back-to-back. A coherent Bell state completes the
     gg->W->gg rotation and returns to '00'; an incoherent gr/rg mixture
     cannot (its dark half stays). High P00 certifies coherence with a
     global-only laser — the certification judges asked about.
  D. Baseline-on-hardware (500 shots): the brief's reference square pulse
     at 5.0 um — the first hardware-vs-hardware baseline comparison.

Usage: submit (default) writes qpu_campaign_batches.json; 'poll' collects.
"""

import json
import sys

import numpy as np
import pulser
from pulser_simulation import QutipEmulator

import score
from pasqal_client import connect
from pasqal_cloud.device import DeviceTypeName

RB = (score.DEVICE.interaction_coeff / (2 * np.pi)) ** (1 / 6)


def get_device_and_layout(sdk):
    spec = sdk.get_device_specs_dict()["FRESNEL_CAN1"]
    device = pulser.devices.Device.from_abstract_repr(spec)
    layout = min(device.pre_calibrated_layouts, key=lambda l: l.number_of_traps)
    return device, layout


def pair_register(layout, target_um):
    """Two traps as close to target_um apart as the lattice allows, centred."""
    coords = layout.coords - layout.coords.mean(0)
    best = None
    n = len(coords)
    for i in range(n):
        for j in range(i + 1, n):
            d = float(np.linalg.norm(coords[i] - coords[j]))
            centre = float(np.linalg.norm((coords[i] + coords[j]) / 2))
            key = (abs(d - target_um), centre)
            if best is None or key < best[0]:
                best = (key, i, j, d)
    _, i, j, d = best
    return layout.define_register(i, j, qubit_ids=["q0", "q1"]), d


def seq_from(amp, det, reg, device):
    seq = pulser.Sequence(reg, device)
    seq.declare_channel("rydberg_global", "rydberg_global")
    seq.add(pulser.Pulse(pulser.CustomWaveform(np.asarray(amp, float)),
                         pulser.CustomWaveform(np.asarray(det, float)),
                         phase=0.0), "rydberg_global")
    seq.measure()
    return seq


def sin2(area, t_ns):
    """Smooth sin^2 envelope with exact pulse area (rad)."""
    t = np.arange(t_ns)
    env = np.sin(np.pi * (t + 0.5) / t_ns) ** 2
    return env * (area / (env.sum() * 1e-3))       # rad/us * ns grid


def build_experiments(device, layout):
    v3 = np.load("v3_r5.0_T260.npz")
    reg_far, d_far = pair_register(layout, 13.0)
    reg_near, d_near = pair_register(layout, 5.0)
    zero = np.zeros(16)
    pi_amp = sin2(np.pi, 1000)
    v3_amp = np.repeat(v3["omega"], 4)
    v3_det = np.repeat(v3["delta"], 4)
    echo_amp = np.concatenate([v3_amp, v3_amp])
    echo_det = np.concatenate([v3_det, v3_det])
    base_amp, base_det = score.reference_pulse(5.0)
    return {
        "A_spam_idle": dict(reg=reg_far, d=d_far, amp=zero, det=zero, runs=250),
        "B_spam_pi": dict(reg=reg_far, d=d_far, amp=pi_amp, det=np.zeros(1000), runs=250),
        "C_echo": dict(reg=reg_near, d=d_near, amp=echo_amp, det=echo_det, runs=500),
        "D_baseline_hw": dict(reg=reg_near, d=d_near, amp=base_amp, det=base_det, runs=500),
    }


def simulate(exp):
    """Noiseless prediction of population per bitstring."""
    reg = exp["reg"]
    seq = seq_from(exp["amp"], exp["det"], reg,
                   pulser.AnalogDevice)  # same physics; AnalogDevice accepts any register
    psi = np.asarray(QutipEmulator.from_sequence(seq).run()
                     .get_final_state().full()).ravel()
    probs = np.abs(psi) ** 2
    # index -> excitation bitstring (1 = ON), pulser basis (r,g), q0 MSB
    out = {}
    for idx, p in enumerate(probs):
        b = format((len(probs) - 1) ^ idx, f"0{int(np.log2(len(probs)))}b")
        if p > 1e-4:
            out[b] = round(float(p), 4)
    return out


def main():
    sdk = connect()
    device, layout = get_device_and_layout(sdk)
    exps = build_experiments(device, layout)

    if len(sys.argv) > 1 and sys.argv[1] == "poll":
        refs = json.load(open("qpu_campaign_batches.json"))
        done = {}
        for name, ref in refs.items():
            b = sdk.get_batch(ref["batch_id"])
            jobs = list(b.ordered_jobs)
            st = jobs[0].status if jobs else b.status
            print(f"{name}: {st}")
            if st == "DONE":
                counts = jobs[0].result or {}
                done[name] = {**ref, "counts": dict(counts)}
        if len(done) == len(refs):
            json.dump(done, open("qpu_campaign_results.json", "w"), indent=1)
            print("ALL DONE — wrote qpu_campaign_results.json")
        return

    # Pre-register noiseless predictions + SPAM-adjusted expectations.
    preds = {}
    for name, exp in exps.items():
        sim = simulate(exp)
        preds[name] = dict(pair_um=round(exp["d"], 2), runs=exp["runs"],
                           noiseless=sim)
    preds["expectations"] = {
        "A_spam_idle": "P(00) ≈ 0.97-0.995 (false-ON floor 0.5-3%/atom)",
        "B_spam_pi": "P(11) ≈ 0.80-0.92 ((1-eps)^2 with eps ≈ 4-10%)",
        "C_echo": "coherent Bell: P(00) ≈ 0.70-0.88; incoherent mixture bound: <= 0.55",
        "D_baseline_hw": "P_bell ≈ 0.82-0.90 (noiseless 0.9926 minus noise+SPAM)",
    }
    json.dump(preds, open("qpu_campaign_predictions.json", "w"), indent=1)
    print("predictions written (pre-registered):")
    for k, v in preds.items():
        if k != "expectations":
            print(f"  {k}: pair={v['pair_um']}um noiseless={v['noiseless']}")

    refs = {}
    for name, exp in exps.items():
        seq = seq_from(exp["amp"], exp["det"], exp["reg"], device)
        batch = sdk.create_batch(serialized_sequence=seq.to_abstract_repr(),
                                 jobs=[{"runs": exp["runs"]}],
                                 device_type=DeviceTypeName.FRESNEL_CAN1,
                                 wait=False)
        refs[name] = dict(batch_id=batch.id, runs=exp["runs"],
                          pair_um=round(exp["d"], 2), status=batch.status)
        print(f"submitted {name}: batch={batch.id}")
    json.dump(refs, open("qpu_campaign_batches.json", "w"), indent=1)


if __name__ == "__main__":
    main()
