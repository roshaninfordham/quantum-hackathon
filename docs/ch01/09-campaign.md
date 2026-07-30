# The closing QPU campaign — four experiments, 1500 shots

*All predictions pre-registered in `ch01/qpu_campaign_predictions.json`
before submission; raw counts in `ch01/qpu_campaign_results.json` with
batch IDs. Registers: a 13.2 µm pair (no blockade) for calibration, the
5.0 µm pair for physics.*

## A + B — SPAM calibration (the numbers that explain everything)

| experiment | counts (shots) | inference |
|---|---|---|
| A: idle, expect `00` | 243× `00`, 7× one-ON (250) | false-ON = **1.4% per atom** |
| B: independent π-pulses, expect `11` | 208× `11`, 39× one-lost, 3× both-lost (250) | excited-readout loss ε = **8.8% per atom** |

The binomial check: with ε = 8.8%, expected one-lost = 2ε(1−ε)·250 ≈ 40
(observed 39) and both-lost ≈ 2 (observed 3). The calibration is
self-consistent to within one count.

**Retroactive correction of every earlier hardware number.** A *perfect*
Bell state, read through this SPAM, shows P_bell ≈ (1−ε)(1−f) ≈ 0.90.
We measured 0.894 → the **SPAM-corrected Bell-state quality is ≈ 0.99**.
The star's 0.684, corrected through (1−ε)³(1−f) ≈ 0.75 for its three
excited atoms → **≈ 0.91**, inside the originally predicted 0.80–0.93
window. Conclusion: the dominant "loss" in both earlier QPU runs was the
camera, not the quantum state.

## C — the coherence echo (certification)

Protocol: the 260 ns Bell pulse applied twice back-to-back. A coherent
Bell state completes the |gg⟩→|W⟩→|gg⟩ rotation and returns to `00`; an
incoherent gr/rg mixture has half its weight in the dark antisymmetric
state, which a global pulse cannot move — bounded at P(00) ≤ ~0.55.

**Measured: P(00) = 95.2%** (476/500; noiseless prediction 98.4%,
pre-registered coherent window 0.70–0.88 — exceeded because the echo's
endpoint |gg⟩ is *cheap to read* (no fragile ON atoms), a subtlety our
window under-credited).

This answers the judges' question — "how do you know it's really
entangled?" — with hardware: **a classical mixture could not return more
than ~55 of 100 shots; ours returned 95.** Done with a global-only laser,
on which a standard Bell test is impossible.

## D — the baseline pulse on real atoms

The brief's reference pulse at r₁: measured P_bell = **0.928** vs our v3's
0.894 (different calibration windows, ~1.5σ apart at 500 shots) —
statistically equivalent, exactly as theory predicts at the *easy*
spacing (noiseless 0.9926 vs 1.000000 is unresolvable at 500 shots).
The differentiating spacing r₂ = 6.5 µm — where the baseline collapses to
0.75 while ours holds 1.000 — cannot be laid out on the calibrated
triangular lattice, so that comparison lives in the simulation column by
hardware necessity, not by our choice.

## Shot ledger (final)

| run | shots |
|---|---|
| Ch1 v3 Bell (batch a1a4d5e8) | 500 |
| Ch2 star MIS (653e8ab0) | 500 |
| Campaign A+B (SPAM) | 500 |
| Campaign C (echo) | 500 |
| Campaign D (baseline) | 500 |
| Ch3 N=10 instance (11553903) | 500 |
| **Total real-atom shots** | **3000** |
