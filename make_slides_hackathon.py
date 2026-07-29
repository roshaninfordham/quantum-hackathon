#!/usr/bin/env python3
"""Combined hackathon deck (Ch01 + Ch02) -> HACKATHON_slides.pdf.

One story: the machine -> entangle two atoms -> the lesson noise taught us
-> make atoms compute -> real hardware, twice. Every line is a speakable
sentence; every number matches the repo. Run from the repo root:
    .venv/bin/python make_slides_hackathon.py
"""

import matplotlib
import numpy as np

matplotlib.use("Agg")
matplotlib.rcParams["pdf.fonttype"] = 42
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Circle, FancyArrow

INK = "#16161d"; ACCENT = "#0f766e"; GOOD = "#15803d"; MUTED = "#6b7280"
BG = "#fbfaf7"; ON = "#22c55e"; OFF = "#cbd5e1"; BAD = "#b91c1c"
W, H = 13.333, 7.5


def new_slide(title, kicker=None):
    fig = plt.figure(figsize=(W, H)); fig.patch.set_facecolor(BG)
    if kicker:
        fig.text(0.055, 0.945, kicker.upper(), fontsize=11, color=ACCENT,
                 fontweight="bold", family="monospace")
    fig.text(0.055, 0.865, title, fontsize=25, color=INK, fontweight="bold")
    fig.text(0.055, 0.032, "Team 6 · Harmoniqs x Pasqal x Microsoft · July 29 2026",
             fontsize=8, color=MUTED)
    fig.text(0.945, 0.032, "github.com/roshaninfordham/quantum-hackathon",
             fontsize=8, color=MUTED, ha="right")
    return fig


def bullets(fig, items, x=0.055, y=0.76, dy=0.072, fs=14, color=INK):
    for body in items:
        fig.text(x, y, "–", fontsize=fs, color=ACCENT, fontweight="bold")
        fig.text(x + 0.022, y, body, fontsize=fs, color=color, va="top",
                 linespacing=1.3)
        y -= dy + body.count("\n") * fs * 0.0024
    return y


def image_panel(fig, path, rect, caption=None):
    ax = fig.add_axes(rect); ax.imshow(mpimg.imread(path)); ax.axis("off")
    if caption:
        fig.text(rect[0] + rect[2] / 2, rect[1] - 0.028, caption,
                 fontsize=9.5, color=MUTED, ha="center")
    return ax


def canvas(fig, rect, xlim, ylim):
    ax = fig.add_axes(rect); ax.set_xlim(*xlim); ax.set_ylim(*ylim)
    ax.set_aspect("equal"); ax.axis("off")
    return ax


def atom(ax, x, y, on, r=0.42, label=None, blockade=None):
    ax.add_patch(Circle((x, y), r, facecolor=ON if on else OFF,
                        edgecolor=INK, lw=1.4, zorder=3))
    ax.text(x, y, "ON" if on else "OFF", ha="center", va="center", fontsize=8,
            fontweight="bold", color="white" if on else MUTED, zorder=4)
    if blockade:
        ax.add_patch(Circle((x, y), blockade, fill=False, ls="--",
                            edgecolor=ACCENT, lw=1.2, alpha=0.7))
    if label:
        ax.text(x, y - r - 0.45, label, ha="center", fontsize=10, color=INK)


_n = [0]
pdf = PdfPages("HACKATHON_slides.pdf")


def save(fig):
    _n[0] += 1
    pdf.savefig(fig)
    import os
    os.makedirs("slides_png", exist_ok=True)
    fig.savefig(f"slides_png/slide_{_n[0]:02d}.png", dpi=130,
                facecolor=fig.get_facecolor())
    plt.close(fig)


# ── 1 · title ────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(W, H)); fig.patch.set_facecolor(BG)
fig.text(0.5, 0.66, "Two challenges, one laser", fontsize=38, color=INK,
         fontweight="bold", ha="center")
fig.text(0.5, 0.55, "Entangling atoms, then making them compute —\n"
         "validated on Pasqal Cloud and run twice on the real quantum computer",
         fontsize=15, color=ACCENT, ha="center", linespacing=1.6)
fig.text(0.28, 0.36, "Challenge 01", fontsize=13, color=MUTED, ha="center")
fig.text(0.28, 0.28, "F: 0.75 → 1.000000", fontsize=21, color=GOOD, ha="center", fontweight="bold")
fig.text(0.72, 0.36, "Challenge 02", fontsize=13, color=MUTED, ha="center")
fig.text(0.72, 0.28, "P_MIS: 0.66 → 0.999999", fontsize=21, color=GOOD, ha="center", fontweight="bold")
fig.text(0.5, 0.14, "Team 6 · A Real Quantum Hackathon · Microsoft Garage NYC",
         fontsize=11, color=MUTED, ha="center")
save(fig)

# ── 2 · the machine in 30 seconds ────────────────────────────────────────
fig = new_slide("The machine, in thirty seconds", "how it works")
ax = canvas(fig, [0.05, 0.15, 0.44, 0.6], (-3.2, 3.2), (-2.6, 2.8))
atom(ax, -1.4, 1.0, False, label="|g⟩ = OFF")
atom(ax, 1.4, 1.0, True, label="|r⟩ = ON")
ax.add_patch(FancyArrow(-2.9, -1.3, 5.4, 0, width=0.09, color=BAD, alpha=0.75))
ax.text(0, -1.85, "one laser shines on ALL atoms at once", ha="center",
        fontsize=10, color=BAD)
bullets(fig, [
    "Every atom is a light switch: ground state\n|g⟩ is OFF, Rydberg state |r⟩ is ON.",
    "One laser drives all atoms together —\nwe control its power Ω(t) and its\nfrequency offset δ(t) over time.",
    "Two excited atoms repel with energy\nV = C₆/r⁶ — so close atoms can never\nboth be ON. That is the blockade.",
    "Everything in this talk is built from\nthose three facts.",
], x=0.53, y=0.75, dy=0.115, fs=13.5)
save(fig)

# ── 3 · challenge 1: the problem ─────────────────────────────────────────
fig = new_slide("Challenge 1 — entangle two atoms", "part one")
bullets(fig, [
    "Take two atoms, both OFF, and one laser pulse. Produce the Bell state |Ψ⁺⟩ = (|gr⟩ + |rg⟩)/√2 —\nexactly one atom ON, but genuinely shared between both. That is entanglement.",
    "We are scored on fidelity, F = |⟨Ψ⁺|ψ(T)⟩|² — how close our final state is to the ideal; 1.0 is perfect.",
    "The twist: do it at two different spacings, 5.0 and 6.5 micrometers, beating the starter pulse at both.",
    "The starter pulse scores 0.9926 at the close spacing — but only 0.7500 at the far one.\nThat gap is the whole challenge.",
], y=0.74, dy=0.115, fs=14.5)
fig.text(0.055, 0.20, "Why it breaks: blockade quality is V/Ω — interaction over drive. At 6.5 µm it drops to 1.8,\n"
         "and 22% of the population leaks into the forbidden both-ON state |rr⟩.",
         fontsize=13.5, color=ACCENT, fontweight="bold", linespacing=1.5)
save(fig)

# ── 4 · c1 evidence ──────────────────────────────────────────────────────
fig = new_slide("Watch the baseline fail — then watch ours not", "challenge 1 · evidence")
image_panel(fig, "ch01/fig_dynamics_r2.png", [0.06, 0.24, 0.88, 0.56],
            "x-axis: time during the pulse (µs) · y-axis: probability of each two-atom configuration")
bullets(fig, [
    "On the left, the baseline: the red curve — the forbidden |rr⟩ state — fills to 22% and the green target stalls at 0.75.",
    "On the right, our pulse: we lower Ω to restore V/Ω ≥ 9, add smooth ramps and a small δ that cancels\nthe Ω²/2V energy shift — red stays at zero, green reaches 1.0.",
], y=0.16, dy=0.06, fs=12.5)
save(fig)

# ── 5 · c1 speed limit ──────────────────────────────────────────────────
fig = new_slide("Then we found the speed limit", "challenge 1 · the frontier")
image_panel(fig, "ch01/fig_time_frontier.png", [0.05, 0.15, 0.62, 0.6],
            "left — x: pulse duration (ns), y: error 1−F on a log scale · right — the winning waveforms")
bullets(fig, [
    "Theory sets a floor: no pulse can\nbeat T = π/(√2·Ω_max) = 177 ns.",
    "We reach F = 0.999999 at 224 ns —\njust 25 ns above that floor.",
    "The full 16-point frontier took\n5.4 seconds of laptop compute:\nan exact 3-state model with\nanalytic gradients.",
    "Why speed matters: under real noise,\nslow pulses collapse (0.999 → 0.73)\nwhile short ones keep 0.93+.\nDuration IS the noise coupling.",
], x=0.70, y=0.74, dy=0.115, fs=12)
save(fig)

# ── 6 · c1 real QPU ─────────────────────────────────────────────────────
fig = new_slide("500 shots on real atoms: 89.4% entangled", "challenge 1 · real hardware")
image_panel(fig, "ch01/screenshots/pasqal_qpu_bitstrings.png", [0.03, 0.13, 0.57, 0.65],
            "Pasqal's own portal · x: measured two-atom outcome · y: % of 500 shots · FRESNEL_CAN1, France")
bullets(fig, [
    "We sent our 260-nanosecond pulse\nto the real machine.",
    "The two tall bars ARE the Bell state:\n'01' at 46% plus '10' at 43% —\n89.4% with exactly one atom ON.",
    "The forbidden '11' shows just 2.4%:\nthe blockade held on real atoms.",
    "We published the expected window\nBEFORE the run — and hit it.",
    "Bonus: the portal labels our pulse\narea 5π/7 — that is π/√2, the\ntwo-atom collective enhancement,\non the machine's own dashboard.",
], x=0.63, y=0.78, dy=0.092, fs=11)
save(fig)

# ── 7 · bridge ──────────────────────────────────────────────────────────
fig = new_slide("Same laser, bigger question: can the atoms compute?", "the bridge")
fig.text(0.055, 0.70, "Challenge 1 taught us three things we carry forward:", fontsize=15, color=INK)
bullets(fig, [
    "The blockade is not a nuisance — it is a CONSTRAINT the hardware enforces for free.",
    "Short, smooth pulses win on real hardware, because noise accumulates with time.",
    "Verify everything: one scorer, predictions published before runs, every number traceable.",
], y=0.60, dy=0.085, fs=14.5)
fig.text(0.055, 0.28, "Challenge 2 uses the blockade as a computer: place atoms so the physics itself\n"
         "encodes a hard puzzle — then one laser sweep makes a photograph reveal the answer.",
         fontsize=15, color=ACCENT, fontweight="bold", linespacing=1.6)
save(fig)

# ── 8 · challenge 2: the puzzle ──────────────────────────────────────────
fig = new_slide("Challenge 2 — the seating puzzle, played by nature", "part two")
ax = canvas(fig, [0.04, 0.13, 0.44, 0.58], (-2.6, 2.6), (-2.6, 2.9))
th = [np.pi/2, np.pi/2 + 2*np.pi/3, np.pi/2 + 4*np.pi/3]
for t in th:
    ax.plot([0, 1.8*np.cos(t)], [0, 1.8*np.sin(t)], color=INK, lw=2, zorder=1)
    atom(ax, 1.8*np.cos(t), 1.8*np.sin(t), True, r=0.36)
atom(ax, 0, 0, False, r=0.36)
ax.text(0, -2.45, "STAR graph: the best answer is\nall 3 leaves ON, hub OFF — unique.",
        ha="center", fontsize=10, color=INK)
ax2 = canvas(fig, [0.50, 0.13, 0.44, 0.58], (-2.6, 2.6), (-2.6, 2.9))
pts = [(1.9*np.cos(np.pi/2 + 2*np.pi*k/5), 1.9*np.sin(np.pi/2 + 2*np.pi*k/5)) for k in range(5)]
for k in range(5):
    x1, y1 = pts[k]; x2, y2 = pts[(k+1) % 5]
    ax2.plot([x1, x2], [y1, y2], color=INK, lw=2, zorder=1)
for k, (x, y) in enumerate(pts):
    atom(ax2, x, y, k in (1, 4), r=0.36)
ax2.text(0, -2.45, "PENTAGON: any 2 non-neighbors ON —\nfive equally good answers.",
         ha="center", fontsize=10, color=INK)
fig.text(0.5, 0.795, "Maximum Independent Set: seat the most people with no two neighbors — a textbook NP-hard problem.\n"
         "Atoms closer than 7.2 µm cannot both be ON, so atom positions ARE the graph, and physics enforces the rule.",
         fontsize=12.5, color=INK, ha="center", linespacing=1.5)
fig.text(0.5, 0.10, "Score: P_MIS — the chance one photograph shows a best answer. Baselines to beat: 0.727 (star), 0.657 (pentagon).",
         fontsize=12, color=ACCENT, ha="center", fontweight="bold")
save(fig)

# ── 9 · c2 method + results ─────────────────────────────────────────────
fig = new_slide("Our sweep: near-perfect on both puzzles", "challenge 2 · results")
image_panel(fig, "ch02/fig_ch02_results.png", [0.04, 0.17, 0.92, 0.58],
            "left/middle — x: time (µs), blue: laser power Ω, red: frequency offset δ · right — x: puzzle, y: P_MIS")
bullets(fig, [
    "Instead of the baseline's slow careful ramp, we let a gradient optimizer shape both laser knobs to maximize\nthe answer probability directly — and for the pentagon we target ALL FIVE valid answers at once.",
    "Result: 0.727 → 0.999998 on the star, 0.657 → 0.999999 on the pentagon — and our sweeps are 4× shorter.",
], y=0.135, dy=0.058, fs=12.5)
save(fig)

# ── 10 · c2 cloud + simplicity ───────────────────────────────────────────
fig = new_slide("1500 photographs, 1500 correct — then we simplified", "challenge 2 · validation")
bullets(fig, [
    "On Pasqal's cloud, every one of 1500 shots across three sweeps showed a correct answer.",
    "The pentagon's five valid answers came back 114, 98, 97, 96 and 95 times — statistically even.\nThe machine holds all five answers at once and samples them fairly. That is visibly quantum.",
    "Then the simplification: just FIVE knobs — one power bump, a tilt, and two sine corrections —\nreach 0.996–0.999, found in thirty seconds, with bandwidth under 1 MHz by construction.",
    "Those five knobs, reused UNCHANGED on bigger rings, still beat the baseline (+0.30 on the 9-ring).\nOn a structurally different graph they lose — an honest limit, and the map for Challenge 3.",
], y=0.72, dy=0.125, fs=14)
save(fig)

# ── 11 · c2 real QPU ────────────────────────────────────────────────────
fig = new_slide("Real atoms pick the right answer, 7 to 1", "challenge 2 · real hardware")
image_panel(fig, "ch02/screenshots/pasqal_qpu_star_bitstrings.png", [0.03, 0.13, 0.57, 0.65],
            "Pasqal's portal · top-left: OUR STAR, drawn by the machine's register viewer · bottom — x: pattern, y: % of 500 shots")
bullets(fig, [
    "Look at the register panel: the hub\nlinked to three leaves — Pasqal's own\nUI is showing the graph we encoded\nin atom positions.",
    "The towering bar is 0111 — the correct\nanswer — at 68.4%. Second place\ngets 9.2%.",
    "It landed below our predicted 80%:\nholding three fragile ON-atoms\ncompounds readout loss. Prediction\npublished first, analysis after.",
    "Total quantum time for all 500 shots:\nhalf a millisecond.",
], x=0.63, y=0.78, dy=0.10, fs=11)
save(fig)

# ── 12 · combined score sheet ────────────────────────────────────────────
fig = new_slide("The score sheet", "summary")
fig.text(0.055, 0.76, "Challenge 1 — Bell-state fidelity F", fontsize=14, color=INK, fontweight="bold")
rows1 = [("", "r₁ = 5.0 µm", "r₂ = 6.5 µm", "duration"),
         ("Baseline", "0.9926", "0.7500", "352 ns"),
         ("Ours (best)", "1.000000", "1.000000", "224–600 ns"),
         ("Real QPU", "89.4% entangled (500 shots)", "n/a on lattice", "260 ns")]
y = 0.71
for i, row in enumerate(rows1):
    for text, xx in zip(row, (0.07, 0.33, 0.60, 0.83)):
        fig.text(xx, y, text, fontsize=12, color=GOOD if i == 2 else INK,
                 fontweight="bold" if i in (0, 2) else "normal")
    y -= 0.048
fig.text(0.055, 0.47, "Challenge 2 — answer probability P_MIS", fontsize=14, color=INK, fontweight="bold")
rows2 = [("", "star K₁,₃", "pentagon C₅", "duration"),
         ("Baseline", "0.727", "0.657", "4000 ns"),
         ("Ours (best)", "0.999998", "0.999999", "1000–2000 ns"),
         ("Cloud", "500/500", "500/500 + 500/500", "—"),
         ("Real QPU", "68.4% exact (7× runner-up)", "n/a on lattice", "1000 ns")]
y = 0.42
for i, row in enumerate(rows2):
    for text, xx in zip(row, (0.07, 0.33, 0.60, 0.83)):
        fig.text(xx, y, text, fontsize=12, color=GOOD if i == 2 else INK,
                 fontweight="bold" if i in (0, 2) else "normal")
    y -= 0.048
fig.text(0.055, 0.13, "Both stages completed. Every number regenerates from the public repo; every hardware claim has a batch ID.",
         fontsize=12.5, color=ACCENT, fontweight="bold")
save(fig)

# ── 13 · closing ────────────────────────────────────────────────────────
fig = new_slide("What we're taking home", "closing")
bullets(fig, [
    "A physics diagnosis beats a black-box search: one number, V/Ω, explained both baseline failures.",
    "On real hardware, pulse duration is the noise coupling — we measured the ranking flip, then designed for it.",
    "Five interpretable knobs get you within half a percent of full optimal control — and they transfer across\na graph family at zero cost. That is the recipe that scales to Challenge 3's 80-atom instances.",
    "Discipline compounds: one scorer per challenge, predictions published before every hardware run,\nfailures analyzed in the open. Two QPU runs, both informative — one confirmed, one taught us SPAM.",
    "Thanks to the Pasqal stack: Pulser's device models, the free cloud emulator, and FRESNEL_CAN1 —\nwhose portal drew our graph back at us.",
], y=0.72, dy=0.115, fs=14)
save(fig)

pdf.close()
print(f"wrote HACKATHON_slides.pdf ({_n[0]} slides) + slides_png/")
