# Challenge 03 — beat published hardware results at scale

## The task (from the deck)

Reproduce the MIS instances of **arXiv:2511.22967** (*Benchmarking neutral
atom-based quantum processors at scale*) at one or more system sizes,
optimize the full pulse schedule, and score above the published curve at
matched instance size and shot count. Hardware runs cap at 80 atoms.

## The published curve (extracted from the paper)

- **Instances:** DUGGs — *diagonal-connected unit-disk grid graphs*: square
  grids with random site dropout; both nearest neighbours and diagonals are
  edges (unit-disk radius between √2·a and 2a).
- **Metric:** approximation ratio r = (Σ C(xᵢ) − C_worst)/(C_opt − C_worst)
  with C_worst = 0 and **valid solutions only** — i.e. the mean independent-
  set size over valid shots, divided by α(G).
- **Their schedule (QAA):** fixed ramp, Ω up/hold/down, δ swept negative →
  positive; 2–4 µs; **500 shots** per instance.
- **The pasqal_fresnel numbers to beat:**

| qubits | 11 | 13 | 17 | 21 |
|---|---|---|---|---|
| r (QAA, 500 shots) | 0.907 | 0.908 | 0.870 | 0.864 |

## Our instances

Generated to the paper's recipe at the device floor: square grid a = 5.0 µm,
random dropout, connected, edges for every pair under R_b = 7.19 µm —
so 5.0 µm neighbours *and* 7.07 µm diagonals are edges, 10 µm is not.
Committed in `ch03/instances.json` (N = 11, 13, 17 with α = 4, 6, 6).

## The physics head-start (found before any optimization)

The interaction ladder of a DUGG at a = 5.0 µm:

| pair | distance | U = C₆/r⁶ |
|---|---|---|
| grid neighbour (edge) | 5.00 µm | 55.41 rad/µs |
| diagonal (edge!) | 7.07 µm | **6.93 rad/µs** |
| next-nearest (non-edge) | 10.0 µm | 0.87 rad/µs |

The MIS energy window therefore requires **0.87 < δ_f < 6.93 rad/µs** —
the reward per ON atom must beat the strongest *non-edge* tail but stay
below the weakest *edge* penalty. **The deck's starter schedule ends at
δ_f = 12.57 rad/µs — outside the window.** Its final ground state can pay
a diagonal-edge penalty and still profit, so the slow ramp faithfully
prepares configurations that *violate diagonal edges*. That, not
insufficient adiabaticity, is the dominant failure of the baseline on this
instance class — and it is fixed by a number, before any optimizer runs.

## Our approach

1. **Instances + exact scorer** (`score03.py`): sparse Krylov propagation
   (exact to N = 17, dim 131k), α by brute force, the paper's r plus a
   repaired-r (greedy violation removal — standard post-processing).
2. **Reproduce the deck baseline** (6000 ns stretched ramp) on every
   instance — the starter scaffolding, scored honestly.
3. **5-knob CRAB sweep** (same family as ch02, T = 2000 ns), trained on the
   N = 11 instance only, with δ_f seeded *inside the window*; objective =
   expected repaired ratio (smooth, size-independent).
4. **Transfer, zero re-optimization,** to N = 13 and 17 — the recipe
   validated in ch02, now on the paper's own instance class.
5. **Validation outward:** Pasqal Cloud (500-shot sampled r, the paper's
   shot count) and one real-QPU point on a lattice-native instance.

## Honest scope notes

- Our simulated r is noiseless; the paper's numbers are hardware. The
  apples-to-apples claims are (a) our cloud 500-shot runs at matched shots
  and (b) our real-QPU point — with the caveat that FRESNEL_CAN1's
  calibrated layout is triangular, so the QPU instance is a
  triangular-lattice unit-disk graph, not a DUGG (stated, not hidden).
- N = 21 was skipped (131k → 2M dim crosses our laptop's comfortable exact
  limit); the transfer property, not brute size, is our scaling claim.

Results: [`ch03/ch03_results.json`](../../ch03/ch03_results.json), report in
[`ch03/REPORT.md`](../../ch03/REPORT.md).
