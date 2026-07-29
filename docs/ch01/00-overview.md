# Challenge 01 — from first principles


---

## From first principles, in five steps

**1 · The qubit.** Each atom is a two-level system: ground |g⟩ and a highly
excited *Rydberg* state |r⟩. A laser couples them with Rabi frequency Ω(t)
(how hard we drive) and detuning δ(t) (how far off-resonance). Both knobs are
**global** — every atom sees the same light. *→ [../01-challenge.md](01-challenge.md)*

**2 · The interaction.** Two atoms in |r⟩ repel: energy V = C₆/r⁶. At close
spacing this shift is so large the laser cannot excite both — the **Rydberg
blockade**. Blockade radius R_b ≈ 7.2 µm here; both our spacings sit inside it,
but not equally deep. *→ [../01-challenge.md](01-challenge.md)*

**3 · Why blockade creates entanglement.** Driving both atoms from |gg⟩, the
blockade forbids |rr⟩, so the system oscillates between |gg⟩ and the *shared*
single excitation (|gr⟩+|rg⟩)/√2 — which **is** the Bell state we're asked
for. The oscillation runs √2 faster than a single atom (both atoms reach for
the same photon). Stop at the π-pulse time T = π/(√2Ω): done.
*→ [../02-physics.md](02-physics.md), derivation in [05-methods.md §2](05-methods.md)*

**4 · Why the baseline breaks at r₂ — the one number that matters.** Blockade
quality is the ratio **V/Ω**. The reference pulse (Ω = 2π×1 MHz) gives
V/Ω = 8.8 at r₁ (fine: F = 0.993) but **1.83** at r₂ — the "forbidden" |rr⟩
takes 22% of the population and F collapses to 0.75. See it happen:
[fig_dynamics_r2.png](../../ch01/fig_dynamics_r2.png).
*→ single-knob proof: [fig_omega_sweep.png](../../ch01/fig_omega_sweep.png), [05-methods.md §4](05-methods.md)*

**5 · The fix.** V is fixed by geometry, but Ω is ours: slow down (V/Ω ≥ 9),
smooth the edges (sin² ramps), and cancel the small energy shift of the target
state with δ(t) — a shift our optimizer rediscovered to three digits of the
perturbation-theory value Ω²/2V. Result: ≥ 0.9994 at both spacings.
*→ [../02-physics.md](02-physics.md), all parameters in [05-methods.md §5](05-methods.md)*

**6 · Then make it fast.** Slowing down costs coherence on real hardware. Using
optimal control (GRAPE with exact adjoint gradients on the exact 3-state
symmetric model — the full 16-point time–fidelity frontier computes in 5.4 s),
we push to the quantum speed limit: **F = 0.999999 at 224 ns (r₁) and 420 ns
(r₂)** — 6–11× shorter than step 5, near the theoretical bound T = π/(√2·Ω_max)
= 177 ns. *→ [../06-time-optimal.md](06-time-optimal.md), frontier:
[fig_time_frontier.png](../../ch01/fig_time_frontier.png)*

**7 · Then make it real.** Under a Lindblad noise model (Rydberg decay + laser
dephasing) the ranking flips: slow pulses collapse to F ≈ 0.73, short ones keep
0.93–0.97 — duration *is* the noise coupling. We re-optimized under the real
FRESNEL envelope with slew-limited smooth shapes (the scientist's "don't shoot
up"), and sent the winner to the **actual quantum computer** — 500 shots on
FRESNEL_CAN1, two atoms on the calibrated lattice.
*→ [../07-hardware.md](07-hardware.md); independent Julia/Piccolo
cross-validation in [piccolo-solutions/](../../piccolo-solutions/)*

---
