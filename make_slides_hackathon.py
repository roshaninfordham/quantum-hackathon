#!/usr/bin/env python3
"""Combined hackathon deck (Ch01 + Ch02) -> HACKATHON_slides.pdf.

Design rules: max ~5 lines per text block, every acronym defined on the
glossary slide, every number tagged with where it comes from, one
step-by-step flowchart per challenge. Run from repo root:
    .venv/bin/python make_slides_hackathon.py
"""

import matplotlib
import numpy as np

matplotlib.use("Agg")
matplotlib.rcParams["pdf.fonttype"] = 42
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Circle, FancyArrow, FancyBboxPatch

INK = "#16161d"; ACCENT = "#0f766e"; GOOD = "#15803d"; MUTED = "#6b7280"
BG = "#fbfaf7"; ON = "#22c55e"; OFF = "#cbd5e1"; BAD = "#b91c1c"
W, H = 13.333, 7.5


def new_slide(title, kicker=None, subhead=None):
    fig = plt.figure(figsize=(W, H)); fig.patch.set_facecolor(BG)
    if kicker:
        fig.text(0.055, 0.95, kicker.upper(), fontsize=10.5, color=ACCENT,
                 fontweight="bold", family="monospace")
    fig.text(0.055, 0.875, title, fontsize=24, color=INK, fontweight="bold")
    if subhead:
        fig.text(0.055, 0.815, subhead, fontsize=12.5, color=MUTED)
    fig.text(0.055, 0.03, "Team 6 · Harmoniqs x Pasqal x Microsoft · July 29 2026",
             fontsize=8, color=MUTED)
    fig.text(0.945, 0.03, "github.com/roshaninfordham/quantum-hackathon",
             fontsize=8, color=MUTED, ha="right")
    return fig


def lines(fig, items, x=0.055, y=0.73, dy=0.085, fs=14.5, color=INK):
    """Spoken sentences with generous spacing (design rule: max ~5)."""
    for body in items:
        fig.text(x, y, "–", fontsize=fs, color=ACCENT, fontweight="bold")
        fig.text(x + 0.020, y, body, fontsize=fs, color=color, va="top",
                 linespacing=1.4)
        y -= dy + body.count("\n") * fs * 0.0028
    return y


def image_panel(fig, path, rect, caption=None):
    ax = fig.add_axes(rect); ax.imshow(mpimg.imread(path)); ax.axis("off")
    if caption:
        fig.text(rect[0] + rect[2] / 2, rect[1] - 0.030, caption,
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


def flow(fig, steps, y=0.46, x0=0.055, x1=0.945, box_h=0.30):
    """Horizontal numbered flowchart: [(title, sub), ...]."""
    n = len(steps)
    gap = 0.018
    bw = (x1 - x0 - gap * (n - 1)) / n
    for i, (t, sub) in enumerate(steps):
        bx = x0 + i * (bw + gap)
        fig.patches.append(FancyBboxPatch(
            (bx, y - box_h / 2), bw, box_h, transform=fig.transFigure,
            boxstyle="round,pad=0.008", facecolor="white", edgecolor=ACCENT,
            lw=1.6, zorder=2))
        fig.text(bx + 0.012, y + box_h / 2 - 0.045, f"{i + 1}", fontsize=17,
                 color=ACCENT, fontweight="bold", zorder=3)
        fig.text(bx + bw / 2, y + box_h / 2 - 0.075, t, fontsize=11.5,
                 color=INK, fontweight="bold", ha="center", va="top",
                 zorder=3, linespacing=1.25)
        fig.text(bx + bw / 2, y + 0.015, sub, fontsize=9.5, color=MUTED,
                 ha="center", va="top", zorder=3, linespacing=1.3)
        if i < n - 1:
            fig.text(bx + bw + gap / 2, y, "→", fontsize=15, color=ACCENT,
                     ha="center", va="center", zorder=3)


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
fig.text(0.5, 0.55, "First we entangled two atoms. Then we made five atoms solve a puzzle.\n"
         "Checked on Pasqal's cloud — and run twice on the real quantum computer.",
         fontsize=15, color=ACCENT, ha="center", linespacing=1.6)
fig.text(0.28, 0.36, "Challenge 1 score", fontsize=13, color=MUTED, ha="center")
fig.text(0.28, 0.28, "0.75  →  1.000000", fontsize=22, color=GOOD, ha="center", fontweight="bold")
fig.text(0.72, 0.36, "Challenge 2 score", fontsize=13, color=MUTED, ha="center")
fig.text(0.72, 0.28, "0.66  →  0.999999", fontsize=22, color=GOOD, ha="center", fontweight="bold")
fig.text(0.5, 0.14, "Team 6 · A Real Quantum Hackathon · Microsoft Garage NYC",
         fontsize=11, color=MUTED, ha="center")
save(fig)

# ── 2 · the machine ─────────────────────────────────────────────────────
fig = new_slide("The machine, in thirty seconds", "how it works",
                "Pasqal's computer holds single atoms in place with laser 'tweezers', then drives them with one control laser.")
ax = canvas(fig, [0.05, 0.14, 0.42, 0.56], (-3.2, 3.2), (-2.6, 2.8))
atom(ax, -1.4, 1.0, False, label="OFF")
atom(ax, 1.4, 1.0, True, label="ON")
ax.add_patch(FancyArrow(-2.9, -1.3, 5.4, 0, width=0.09, color=BAD, alpha=0.75))
ax.text(0, -1.85, "one laser shines on ALL atoms at once", ha="center",
        fontsize=10, color=BAD)
lines(fig, [
    "Each atom is a switch: OFF (its normal\nstate) or ON (a high-energy state).",
    "One laser drives every atom together.\nWe choose its power and its pitch,\nas functions of time.",
    "Two ON atoms push on each other.\nIf they are close, that push is so big\nthat both being ON is impossible.",
], x=0.52, y=0.72, dy=0.135, fs=14)
save(fig)

# ── 3 · glossary ─────────────────────────────────────────────────────────
fig = new_slide("Six terms — this is all the jargon we need", "glossary")
terms = [
    ("Ω(t)  'omega'", "laser POWER over time. The machine allows up to 12.6 rad/µs (from Pasqal's published spec)."),
    ("δ(t)  'delta'", "laser PITCH (frequency offset) over time — negative discourages ON, positive encourages it."),
    ("Blockade, R_b", "the no-two-ON rule. Its reach R_b ≈ 7.2 µm follows from the machine's spec: R_b = (C₆/Ω)^(1/6)."),
    ("Fidelity F", "Challenge 1's score, defined by the organizers: F = |⟨target|our state⟩|². 1.0 = perfect match."),
    ("MIS · P_MIS", "Maximum Independent Set: biggest group with no two neighbors. P_MIS (Challenge 2's score) = the\nprobability one measurement shows a best answer."),
    ("QPU · shot", "QPU = the real quantum computer (FRESNEL, in France). A shot = one run + one photo of the atoms.\nAll scores use 500 shots — the count fixed in the challenge brief."),
]
y = 0.74
for name, desc in terms:
    fig.text(0.055, y, name, fontsize=13.5, color=ACCENT, fontweight="bold", family="monospace")
    fig.text(0.28, y, desc, fontsize=12.5, color=INK, va="top", linespacing=1.35)
    y -= 0.105
save(fig)

# ── 4 · ch1 problem ─────────────────────────────────────────────────────
fig = new_slide("Challenge 1 — make two atoms share one excitation", "part one · the task")
fig.text(0.055, 0.775, "GIVEN by the organizers:", fontsize=12, color=MUTED, fontweight="bold")
lines(fig, [
    "Two atoms, both OFF, at spacing 5.0 µm — and then again at 6.5 µm.",
    "A starter pulse to beat. Its scores: F = 0.9926 (close pair) and F = 0.7500 (far pair).",
    "The target: the Bell state (|gr⟩+|rg⟩)/√2 — one atom ON, but genuinely shared between both.",
], y=0.73, dy=0.075, fs=14)
fig.text(0.055, 0.46, "WE design:", fontsize=12, color=MUTED, fontweight="bold")
lines(fig, [
    "The laser power Ω(t) and pitch δ(t), inside the machine's published limits, at both spacings.",
], y=0.415, dy=0.07, fs=14)
fig.text(0.055, 0.28, "The whole challenge in one sentence: the starter pulse loses 25% at the far spacing —\n"
         "find pulses that do not.",
         fontsize=15, color=ACCENT, fontweight="bold", linespacing=1.5)
save(fig)

# ── 5 · ch1 diagnosis ────────────────────────────────────────────────────
fig = new_slide("Where the missing 25% goes", "part one · diagnosis",
                "We computed the state at every moment of the pulse (exact simulation). Red = the forbidden both-ON state.")
image_panel(fig, "ch01/fig_dynamics_r2.png", [0.06, 0.235, 0.88, 0.54],
            "x-axis: time during the pulse, in microseconds · y-axis: probability of each two-atom outcome")
lines(fig, [
    "Left, the starter pulse at 6.5 µm: the atoms are far apart, the blockade is weak, and 22% leaks into\nthe forbidden both-ON state (red). The target (green) gets stuck at 0.75.",
    "Right, our pulse: gentler power restores the blockade, so red stays at zero and green reaches 1.0.",
], y=0.155, dy=0.062, fs=12.5)
save(fig)

# ── 6 · ch1 solution flowchart ───────────────────────────────────────────
fig = new_slide("How we solved it, step by step", "part one · our approach")
flow(fig, [
    ("Build the referee", "one program that scores\nany pulse exactly the way\nthe judges do"),
    ("Reproduce the\nbaseline", "0.9926 and 0.7500 —\nnow 'beat it' is a\ntestable claim"),
    ("Diagnose with\nphysics", "one ratio (push ÷ power)\nexplains the failure;\nlower the power to fix it"),
    ("Optimize for\nspeed", "a standard method (GRAPE,\nfrom NMR research) shapes\nthe pulse near the physical\nspeed limit"),
    ("Validate\noutward", "device rule-check → cloud,\n500 shots → the real\nmachine, 500 shots"),
], y=0.55)
lines(fig, [
    "Each step is checked before the next: the referee has self-tests, the optimizer's math is verified\nagainst brute force, and we publish our predicted hardware numbers BEFORE each real run.",
    "Result: fidelity 1.000000 at both spacings, with pulses 224–600 nanoseconds long —\nup to 11× shorter than the starter pulse, which matters because noise grows with time.",
], y=0.30, dy=0.085, fs=13.5)
save(fig)

# ── 7 · ch1 results ─────────────────────────────────────────────────────
fig = new_slide("Challenge 1 results", "part one · scores",
                "All scores from the same exact simulator the judges use; cloud columns are measured, 500 shots each.")
image_panel(fig, "ch01/ch01_results.png", [0.05, 0.17, 0.9, 0.58],
            "top row: our pulse shapes (x: time; blue: power Ω, red: pitch δ) · bottom-left: score bars vs baseline ·"
            " bottom-right: cloud measurements (dots) vs simulation (circles) — they agree")
lines(fig, [
    "Grey bars are the starter pulse: 0.9926 and 0.7500. Green and blue bars are ours: 0.999+ everywhere.",
], y=0.115, dy=0.05, fs=12.5)
save(fig)

# ── 8 · ch1 real QPU ────────────────────────────────────────────────────
fig = new_slide("On the real machine: 89.4% entangled", "part one · real hardware")
image_panel(fig, "ch01/screenshots/pasqal_qpu_bitstrings.png", [0.03, 0.13, 0.57, 0.64],
            "Pasqal's own results page · x: the four possible photos of two atoms · y: % of 500 shots")
lines(fig, [
    "We sent our 260-nanosecond pulse\nto FRESNEL_CAN1, in France.",
    "The two tall bars are the Bell state:\none atom ON, either one — together\n89.4% of all 500 photos.",
    "The bars are equal, as the physics\ndemands. The forbidden both-ON\nresult appears in only 2.4%.",
    "We published the expected range\nbefore the run — the result landed\ninside it.",
], x=0.63, y=0.75, dy=0.115, fs=12)
save(fig)

# ── 9 · bridge ──────────────────────────────────────────────────────────
fig = new_slide("Same laser, bigger question: can the atoms compute?", "the bridge")
lines(fig, [
    "Challenge 1 treated the blockade as an obstacle. Challenge 2 uses it as a resource:",
    "The no-two-ON rule is exactly the rule of a famous puzzle — and the hardware enforces it for free.",
], y=0.72, dy=0.09, fs=15)
fig.text(0.055, 0.50, "Also carried forward from Challenge 1:", fontsize=12, color=MUTED, fontweight="bold")
lines(fig, [
    "Short pulses beat long ones on real hardware (noise grows with time).",
    "One referee program per challenge; predictions published before every hardware run.",
], y=0.455, dy=0.08, fs=14)
save(fig)

# ── 10 · ch2 problem ─────────────────────────────────────────────────────
fig = new_slide("Challenge 2 — the seating puzzle", "part two · the task",
                "Maximum Independent Set (MIS): seat the most people so that no two sit next to each other.")
ax = canvas(fig, [0.05, 0.12, 0.42, 0.55], (-2.6, 2.6), (-2.6, 2.9))
th = [np.pi/2, np.pi/2 + 2*np.pi/3, np.pi/2 + 4*np.pi/3]
for t in th:
    ax.plot([0, 1.8*np.cos(t)], [0, 1.8*np.sin(t)], color=INK, lw=2, zorder=1)
    atom(ax, 1.8*np.cos(t), 1.8*np.sin(t), True, r=0.36)
atom(ax, 0, 0, False, r=0.36)
ax.text(0, -2.45, "STAR graph (4 atoms): best answer is\nthe 3 outer atoms ON — only one answer.",
        ha="center", fontsize=9.5, color=INK)
ax2 = canvas(fig, [0.51, 0.12, 0.42, 0.55], (-2.6, 2.6), (-2.6, 2.9))
pts = [(1.9*np.cos(np.pi/2 + 2*np.pi*k/5), 1.9*np.sin(np.pi/2 + 2*np.pi*k/5)) for k in range(5)]
for k in range(5):
    x1, y1 = pts[k]; x2, y2 = pts[(k+1) % 5]
    ax2.plot([x1, x2], [y1, y2], color=INK, lw=2, zorder=1)
for k, (x, y) in enumerate(pts):
    atom(ax2, x, y, k in (1, 4), r=0.36)
ax2.text(0, -2.45, "PENTAGON (5 atoms): any 2 non-neighbors\nON — five equally correct answers.",
         ha="center", fontsize=9.5, color=INK)
lines(fig, [
    "GIVEN: these two graphs, and a starter sweep scoring 0.727 (star) and 0.657 (pentagon).",
    "WE design: where each atom sits (lines = pairs closer than R_b) and the sweep Ω(t), δ(t). A photo at\nthe end reads out the answer: ON atoms are the chosen seats.",
], y=0.755, dy=0.062, fs=12.5)
save(fig)

# ── 11 · ch2 solution flowchart ─────────────────────────────────────────
fig = new_slide("How we solved it, step by step", "part two · our approach")
flow(fig, [
    ("Draw the graph\nwith atoms", "place atoms so 'closer\nthan R_b' gives exactly\nthe target edges —\nverified in code"),
    ("Build the referee", "P_MIS from the exact\nstate; self-tests catch\nconvention mistakes"),
    ("Reproduce the\nbaseline", "0.727 and 0.657, from\nthe brief's own sweep\nparameters"),
    ("Optimize the\nsweep", "GRAPE again — but aimed\nat ALL correct answers at\nonce (the pentagon has 5)"),
    ("Simplify, then\nvalidate", "a 5-knob version for\nhardware → cloud → the\nreal machine"),
], y=0.55)
lines(fig, [
    "The key idea in step 4: the starter sweep is slow and careful, yet still spills. We stop being careful\nand let the optimizer find the best route directly — scores jump to 0.999998 and 0.999999.",
    "And our sweeps take 1000 nanoseconds — one quarter of the starter's 4000 — which wins big under noise.",
], y=0.30, dy=0.085, fs=13.5)
save(fig)

# ── 12 · ch2 results + cloud ─────────────────────────────────────────────
fig = new_slide("Challenge 2 results — and 1500 perfect photos", "part two · scores")
image_panel(fig, "ch02/fig_ch02_results.png", [0.04, 0.235, 0.92, 0.54],
            "left/middle — x: time (µs), blue: power Ω, red: pitch δ · right — x: puzzle, y: score P_MIS")
lines(fig, [
    "On Pasqal's cloud: 1500 shots across three sweeps, and every single photo showed a correct answer.",
    "The pentagon's five answers came back 114, 98, 97, 96, 95 times — evenly, as quantum theory predicts:\nthe machine holds all five answers at once and samples them fairly.",
], y=0.155, dy=0.062, fs=12.5)
save(fig)

# ── 13 · ch2 real QPU ────────────────────────────────────────────────────
fig = new_slide("Real atoms pick the right answer, 7 to 1", "part two · real hardware")
image_panel(fig, "ch02/screenshots/pasqal_qpu_star_bitstrings.png", [0.03, 0.13, 0.57, 0.64],
            "Pasqal's results page · top-left: our star, drawn by the machine itself · bottom — x: measured pattern, y: % of 500 shots")
lines(fig, [
    "The register view shows the machine\nholding OUR graph: hub plus three\nleaves, in real optical tweezers.",
    "The towering bar, 0111, is the correct\nanswer: 68.4% of 500 photos.\nThe runner-up gets 9.2%.",
    "That is below the 80% we predicted:\nkeeping three atoms ON compounds\nreadout losses. We published the\nprediction first, the analysis after.",
], x=0.63, y=0.75, dy=0.125, fs=12)
save(fig)

# ── 14 · score sheet ─────────────────────────────────────────────────────
fig = new_slide("The score sheet", "summary")
fig.text(0.055, 0.765, "Challenge 1 — fidelity F (score defined in the brief)", fontsize=13.5, color=INK, fontweight="bold")
rows1 = [("", "close pair (5.0 µm)", "far pair (6.5 µm)", "pulse length"),
         ("Starter pulse", "0.9926", "0.7500", "352 ns"),
         ("Ours (best)", "1.000000", "1.000000", "224–600 ns"),
         ("Real machine", "89.4% entangled (500 shots)", "n/a on this lattice", "260 ns")]
y = 0.715
for i, row in enumerate(rows1):
    for text, xx in zip(row, (0.07, 0.32, 0.60, 0.84)):
        fig.text(xx, y, text, fontsize=12, color=GOOD if i == 2 else INK,
                 fontweight="bold" if i in (0, 2) else "normal")
    y -= 0.048
fig.text(0.055, 0.475, "Challenge 2 — answer probability P_MIS (score defined in the brief)", fontsize=13.5, color=INK, fontweight="bold")
rows2 = [("", "star (4 atoms)", "pentagon (5 atoms)", "sweep length"),
         ("Starter sweep", "0.727", "0.657", "4000 ns"),
         ("Ours (best)", "0.999998", "0.999999", "1000–2000 ns"),
         ("Cloud, 500-shot runs", "500/500 correct", "500/500, twice", "—"),
         ("Real machine", "68.4% exact (7× runner-up)", "n/a on this lattice", "1000 ns")]
y = 0.425
for i, row in enumerate(rows2):
    for text, xx in zip(row, (0.07, 0.32, 0.60, 0.84)):
        fig.text(xx, y, text, fontsize=12, color=GOOD if i == 2 else INK,
                 fontweight="bold" if i in (0, 2) else "normal")
    y -= 0.048
fig.text(0.055, 0.125, "Both stages completed. Every number regenerates from our public repository;\n"
         "every hardware claim carries the machine's own batch ID.",
         fontsize=12.5, color=ACCENT, fontweight="bold", linespacing=1.4)
save(fig)

# ── 15 · closing ────────────────────────────────────────────────────────
fig = new_slide("What we're taking home", "closing")
lines(fig, [
    "Diagnose before you optimize: one physics ratio (push ÷ power) explained both baseline failures.",
    "On real hardware, time is the enemy: our pulses are 4–11× shorter than the starters, and that is\nexactly why they survive noise.",
    "Five simple knobs got within half a percent of full optimal control — and carried over to bigger\npuzzles without re-tuning. That is the recipe for the 80-atom instances of Challenge 3.",
    "Trust is a workflow: one referee per challenge, predictions published before both hardware runs,\nand the one miss analyzed in the open.",
    "Thank you to the Pasqal stack — the Pulser toolkit, the free cloud emulator, and the FRESNEL\nmachine that drew our graph back at us.",
], y=0.73, dy=0.115, fs=14)
save(fig)

pdf.close()
print(f"wrote HACKATHON_slides.pdf ({_n[0]} slides) + slides_png/")
