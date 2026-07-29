# Challenge 02 — Encode a graph in atom positions, then solve it

## The task, in plain words

Challenge 01 was "make two atoms dance together." Challenge 02 is
"make 4–5 atoms *compute something*": place the atoms so their geometry
encodes a puzzle, then design one global laser sweep so that simply
*photographing* the atoms at the end reads out the puzzle's answer.

**The puzzle: Maximum Independent Set (MIS).** Given a network (graph),
find the largest set of nodes where no two are connected. It's NP-hard in
general — the textbook "hard problem" — and it's the native problem of
Rydberg machines, which is why this challenge exists.

## How atoms encode a graph

Two atoms within the blockade radius R_b cannot both be excited — that's a
*physical* edge constraint. So:

- **vertex** = atom
- **edge** = pair of atoms closer than R_b (here R_b ≈ 7.19 µm at the
  baseline drive)
- **independent set** = any set of atoms that could all be excited at once
- an atom photographed in |r⟩ ⇒ "this vertex is in the candidate set"

Physics does the constraint-checking for free: configurations violating an
edge cost interaction energy U = C₆/r⁶ and are pushed out of the ground
state. Getting the *maximum* set is then an energy-minimization: each
excitation is rewarded by the final detuning δ_f, so more excitations =
lower energy, as long as no edge is violated. The window that makes this
exact is **U_diag < δ_f < U_nn** — reward big enough to want every legal
excitation (beats the residual next-neighbor tail U_diag), small enough
never to pay for an edge violation (below U_nn).

## The two graphs (from the deck)

| | G_A: star K₁,₃ | G_B: cycle C₅ |
|---|---|---|
| atoms | 4 (center + 3 leaves, ρ = 5.5 µm) | 5 (pentagon, side s = 5.5 µm) |
| edges | center–leaf ×3 (5.5 < R_b) | the 5 sides (5.5 < R_b) |
| non-edges | leaf–leaf (√3·5.5 = 9.53 > R_b) | the 5 diagonals (1.618·5.5 = 8.90 > R_b) |
| α(G) | 3 | 2 |
| MIS solutions | exactly 1 (the three leaves) | 5 (the non-adjacent pairs) |
| interactions | U_nn = 31.3 rad/µs | U_nn = 31.3, U_diag = 1.74 rad/µs |

Register validity is not assumed — `ch02/score02.py::check_unit_disk`
verifies every pair against R_b programmatically, and the selftest runs it
on every scoring session.

## Score and baseline

**P_MIS** = probability that one photograph shows an independent set of
exactly maximum size α(G). (For C₅ that's the sum over all five valid
answers — the machine is allowed to return any of them.)

**Baseline** (deck starter kit, computed exactly in our scorer):
T = 4000 ns, Ω = 2π×1 MHz trapezoid (252 ns rise/fall), δ swept linearly
−2π×2 → +2π×2 MHz:

| graph | baseline P_MIS |
|---|---|
| star K₁,₃ | **0.727135** |
| cycle C₅ | **0.657049** |

**Success:** P_MIS strictly above these, same graphs, device envelope.

## Why the baseline underperforms (the physics to exploit)

The linear sweep is an *adiabatic algorithm*: start in |g…g⟩ (ground state
at δ < 0), drag the system slowly to δ_f > 0 where the ground state *is*
the MIS manifold. It loses probability at the **minimum spectral gap**,
where the ground state reorganizes from "no excitations" to "the MIS
pattern" — a small window somewhere mid-sweep. A linear ramp wastes its
time budget cruising through easy regions at the same speed it crosses the
danger zone. The fixes, in increasing power:

1. **Slow down at the gap** (locally-adiabatic schedules)
2. **Shape Ω(t)** — the drive itself sets the gap size
3. **Full optimal control** (our approach): stop thinking adiabatically;
   let GRAPE find whatever trajectory maximizes P_MIS directly, including
   diabatic shortcuts the adiabatic picture forbids.

→ Methods, results, and the verification story: [02-methods.md](02-methods.md)
