#!/usr/bin/env python3
"""Challenge 02 slide deck -> CH02_slides.pdf (16:9, newbie-friendly).

Every number matches the repo; drawn graphics explain the encoding.
Regenerate: .venv/bin/python ch02/make_slides_ch02.py
"""

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Circle, FancyArrow

INK = "#16161d"; ACCENT = "#0f766e"; GOOD = "#15803d"; BAD = "#b91c1c"
MUTED = "#6b7280"; BG = "#fbfaf7"; ON = "#22c55e"; OFF = "#cbd5e1"
W, H = 13.333, 7.5


def new_slide(title, kicker=None):
    fig = plt.figure(figsize=(W, H)); fig.patch.set_facecolor(BG)
    if kicker:
        fig.text(0.055, 0.945, kicker.upper(), fontsize=11, color=ACCENT,
                 fontweight="bold", family="monospace")
    fig.text(0.055, 0.865, title, fontsize=26, color=INK, fontweight="bold")
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
    ax.text(x, y, "ON" if on else "OFF", ha="center", va="center",
            fontsize=8, fontweight="bold",
            color="white" if on else MUTED, zorder=4)
    if blockade:
        ax.add_patch(Circle((x, y), blockade, fill=False, ls="--",
                            edgecolor=ACCENT, lw=1.2, alpha=0.7))
    if label:
        ax.text(x, y - r - 0.45, label, ha="center", fontsize=10, color=INK)


pdf = PdfPages("CH02_slides.pdf")

# ── 1 · title ────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(W, H)); fig.patch.set_facecolor(BG)
fig.text(0.5, 0.62, "Making atoms solve a puzzle", fontsize=36, color=INK,
         fontweight="bold", ha="center")
fig.text(0.5, 0.50, "Challenge 02 — encode a graph in atom positions, "
         "photograph the answer", fontsize=15, color=ACCENT, ha="center")
fig.text(0.5, 0.34, "Success probability 0.727 / 0.657 (baseline)  →  0.999998 / 0.999999 (ours)\n"
         "Cloud: 1500 of 1500 photographs showed a correct answer · also run on real atoms",
         fontsize=13.5, color=INK, ha="center", linespacing=1.7)
fig.text(0.5, 0.12, "Team 6 · A Real Quantum Hackathon · Harmoniqs x Pasqal x Microsoft",
         fontsize=11, color=MUTED, ha="center")
pdf.savefig(fig); plt.close(fig)

# ── 2 · atoms are light switches ─────────────────────────────────────────
fig = new_slide("First: an atom is just a light switch", "the basics")
ax = canvas(fig, [0.05, 0.17, 0.42, 0.58], (-3, 3), (-2.4, 2.6))
atom(ax, -1.5, 0.8, False, label="|g⟩ = OFF")
atom(ax, 1.5, 0.8, True, label="|r⟩ = ON")
ax.add_patch(FancyArrow(-2.7, -1.5, 5.0, 0, width=0.09, color=BAD, alpha=0.75))
ax.text(0, -1.95, "one laser shines on ALL atoms at once", ha="center",
        fontsize=10, color=BAD)
bullets(fig, [
    "Every atom is OFF (|g⟩) or ON (|r⟩).",
    "We cannot poke atoms one by one — one\nlaser hits all of them together.",
    "Our only two knobs, over time:\nΩ(t) = laser power, δ(t) = frequency offset.",
    "Plus one more freedom: WHERE we\nplace the atoms before we start.",
], x=0.53, y=0.74, dy=0.115, fs=13.5)
pdf.savefig(fig); plt.close(fig)

# ── 3 · the puzzle (classroom analogy) ───────────────────────────────────
fig = new_slide("The puzzle: seat the most people, no neighbors", "maximum independent set")
bullets(fig, [
    "Classroom rule: no two students in adjacent seats. Question: what is the MOST students you can seat?",
    "That is the Maximum Independent Set (MIS) — a textbook 'hard' problem: the options explode as graphs grow.",
    "The trick of this challenge: atoms that sit close CANNOT both be ON (physics forbids it — the 'blockade').",
    "So the seating rule is enforced by nature, for free. Turn the laser sweep on, photograph the atoms:\nthe ON atoms ARE the seated students.",
], y=0.74, dy=0.105, fs=14.5)
fig.text(0.055, 0.20, "We never check combinations one-by-one. The quantum system explores them together,\n"
         "and we shape the laser so the best answer is what the camera sees.",
         fontsize=14, color=ACCENT, fontweight="bold", linespacing=1.5)
pdf.savefig(fig); plt.close(fig)

# ── 4 · distance = friendship (encoding) ────────────────────────────────
fig = new_slide("How atoms become a graph: distance decides the edges", "the encoding")
ax = canvas(fig, [0.05, 0.14, 0.55, 0.62], (-1.2, 12.6), (-2.4, 3.8))
atom(ax, 1.0, 0.8, False, blockade=1.55); atom(ax, 3.0, 0.8, False, blockade=1.55)
ax.text(2.0, 3.15, "close (< 7.2 µm): circles overlap\n= EDGE — can't both be ON",
        ha="center", fontsize=9.5, color=INK)
ax.plot([1.0, 3.0], [0.8, 0.8], color=INK, lw=2, zorder=1)
atom(ax, 7.6, 0.8, True, blockade=1.55); atom(ax, 10.9, 0.8, True, blockade=1.55)
ax.text(9.25, 3.15, "far apart (> 7.2 µm): no overlap\n= NO edge — both may be ON",
        ha="center", fontsize=9.5, color=INK)
bullets(fig, [
    "Each atom = one dot (vertex)\nof the graph.",
    "Two atoms closer than the blockade\nradius R_b ≈ 7.2 µm = one edge.",
    "So we DRAW the puzzle with tweezers:\natom positions are the graph.",
    "We verified every distance in code —\nthe register is exactly the target graph.",
], x=0.63, y=0.74, dy=0.115, fs=12.5)
pdf.savefig(fig); plt.close(fig)

# ── 5 · our two puzzles ─────────────────────────────────────────────────
fig = new_slide("The two puzzles we were given", "the graphs")
ax = canvas(fig, [0.04, 0.13, 0.44, 0.6], (-2.6, 2.6), (-2.6, 2.9))
th = [np.pi/2, np.pi/2 + 2*np.pi/3, np.pi/2 + 4*np.pi/3]
for t in th:
    ax.plot([0, 1.8*np.cos(t)], [0, 1.8*np.sin(t)], color=INK, lw=2, zorder=1)
    atom(ax, 1.8*np.cos(t), 1.8*np.sin(t), True, r=0.36)
atom(ax, 0, 0, False, r=0.36)
ax.text(0, -2.45, "STAR: hub + 3 leaves.\nBest answer: the 3 leaves ON, hub OFF (unique).",
        ha="center", fontsize=10, color=INK)
ax2 = canvas(fig, [0.52, 0.13, 0.44, 0.6], (-2.6, 2.6), (-2.6, 2.9))
pts = [(1.9*np.cos(np.pi/2 + 2*np.pi*k/5), 1.9*np.sin(np.pi/2 + 2*np.pi*k/5)) for k in range(5)]
for k in range(5):
    x1, y1 = pts[k]; x2, y2 = pts[(k+1) % 5]
    ax2.plot([x1, x2], [y1, y2], color=INK, lw=2, zorder=1)
for k, (x, y) in enumerate(pts):
    atom(ax2, x, y, k in (1, 4), r=0.36)
ax2.text(0, -2.45, "PENTAGON: 5 in a ring.\nBest answer: any 2 non-neighbors ON — 5 equally good answers.",
         ha="center", fontsize=10, color=INK)
fig.text(0.5, 0.79, "Score = P_MIS: the chance one photograph shows a best answer. Beat the starter sweep.",
         fontsize=13, color=ACCENT, ha="center", fontweight="bold")
pdf.savefig(fig); plt.close(fig)

# ── 6 · baseline + our method ────────────────────────────────────────────
fig = new_slide("The starter sweep vs what we did", "method")
bullets(fig, [
    "Starter sweep (the baseline): slowly tilt the laser frequency for 4000 ns — like carrying a full cup\nvery carefully. Score: star 0.727, pentagon 0.657. It spills at the hardest moment.",
    "Our approach: stop being careful, be OPTIMAL. We let a gradient optimizer (GRAPE) shape both laser\nknobs freely, to directly maximize the chance the photo shows a best answer.",
    "Key detail: the pentagon has FIVE equally-right answers. We optimize toward ALL of them at once\n(a 'projector' target) — the final state holds each answer at exactly 20%.",
    "Every result is double-checked in Pulser — the judges' own simulator (agreement: 7 decimal places).",
], y=0.74, dy=0.125, fs=13.5)
fig.text(0.055, 0.17, "Compute cost: all six optimizations ≈ 2 minutes on a laptop. Our sweeps are also 4× SHORTER\n"
         "than the baseline (1000 ns vs 4000 ns) — shorter = less time for real-world noise to corrupt the answer.",
         fontsize=12.5, color=ACCENT, style="italic", linespacing=1.5)
pdf.savefig(fig); plt.close(fig)

# ── 7 · results ─────────────────────────────────────────────────────────
fig = new_slide("Result: near-perfect on both puzzles", "results")
image_panel(fig, "fig_ch02_results.png", [0.04, 0.15, 0.92, 0.6],
            "left/middle — x: time (µs), blue: laser power Ω, red: frequency offset δ · "
            "right — x: puzzle, y: success probability P_MIS")
bullets(fig, [
    "Grey bars (baseline): 0.727 and 0.657.  Green bars (ours): 0.999998 and 0.999999.",
], y=0.13, dy=0.05, fs=13)
pdf.savefig(fig); plt.close(fig)

# ── 8 · cloud validation ────────────────────────────────────────────────
fig = new_slide("Pasqal Cloud: 1500 photographs, 1500 correct answers", "validation")
bullets(fig, [
    "We sent 3 optimized sweeps to Pasqal's cloud emulator, 500 shots each.",
    "Star: 500/500 photos showed exactly the right answer (0111 = hub OFF, leaves ON).",
    "Pentagon (1000 ns): 500/500 correct — split across ALL FIVE valid answers:\n114, 98, 97, 96, 95 — statistically even.",
    "That even split is a quantum signature: the machine doesn't pick one answer —\nit holds all five at once and samples them fairly.",
    "Pentagon (2000 ns): 500/500 again. Every batch ID is recorded in the repo for audit.",
], y=0.74, dy=0.11, fs=14)
pdf.savefig(fig); plt.close(fig)

# ── 9 · low-bandwidth + transfer ─────────────────────────────────────────
fig = new_slide("Then we asked: how simple can the winning sweep be?", "low bandwidth · transfer")
image_panel(fig, "fig_ch02_lowbw.png", [0.03, 0.15, 0.94, 0.58],
            "left — x: number of knobs, y: P_MIS · middle — the 5-knob sweep vs the 125-knob one · "
            "right — x: new graphs, y: P_MIS with ZERO re-tuning")
bullets(fig, [
    "FIVE knobs (vs 125) reach 0.996–0.999 — found in ~30 seconds, and smooth enough for any hardware.",
    "The same 5 knobs, re-used unchanged on bigger rings: still beat the baseline (+0.30 on the 9-ring).\nOn a structurally different random graph they lose — honest limit, stated as a finding.",
], y=0.135, dy=0.055, fs=12)
pdf.savefig(fig); plt.close(fig)

# ── 10 · QPU bitstrings ─────────────────────────────────────────────────
fig = new_slide("Real atoms, real answer: the machine drew our star", "real hardware · FRESNEL_CAN1")
image_panel(fig, "screenshots/pasqal_qpu_star_bitstrings.png", [0.03, 0.13, 0.57, 0.65],
            "Pasqal's portal · top-left: OUR STAR, drawn by the machine's register viewer · "
            "bottom — x: measured pattern, y: % of 500 shots")
bullets(fig, [
    "Register panel: q0 hub linked to q1–q3\n— Pasqal's own UI shows the graph we\nencoded in atom positions.",
    "The towering bar: 0111 = the correct\nanswer, at 68.4% (342 of 500 shots).\nSecond place: 9.2%.",
    "Real atoms solve the puzzle decisively\n— the right answer wins by 7×.",
    "Below our predicted 80–93% window:\nholding 3 fragile ON-atoms compounds\nreadout loss — we published the\nprediction first and the analysis after.",
], x=0.63, y=0.76, dy=0.105, fs=11.5)
pdf.savefig(fig); plt.close(fig)

# ── 11 · QPU pulse ──────────────────────────────────────────────────────
fig = new_slide("The sweep the machine actually played", "real hardware · the pulse")
image_panel(fig, "screenshots/pasqal_qpu_star_pulse.png", [0.03, 0.13, 0.57, 0.65],
            "Pasqal portal, Pulses tab · x: time 0–1000 ns · purple: laser power Ω(t) · white: frequency offset δ(t)")
bullets(fig, [
    "1000 nanoseconds, one smooth bump\nof laser power (purple) — our\n5-knob, hardware-friendly sweep.",
    "The white curve is the story: it starts\nNEGATIVE (being ON is penalized)\nand ends POSITIVE (being ON is\nrewarded — but only where the\nblockade allows it).",
    "That tilt walks the atoms from\n'all OFF' to 'the best seating plan'.",
    "Bandwidth ≤ 1 MHz by construction —\nwell inside what the hardware can play.",
], x=0.63, y=0.76, dy=0.105, fs=11.5)
pdf.savefig(fig); plt.close(fig)

# ── 11b · the metric + why it matters ───────────────────────────────────
fig = new_slide("The score, and why anyone should care", "metric · commercial value")
fig.text(0.5, 0.72, "P_MIS  =  P( one photograph shows a best answer )",
         fontsize=24, color=INK, ha="center", fontweight="bold")
fig.text(0.25, 0.545, "+0.34", fontsize=46, color=GOOD, ha="center", fontweight="bold")
fig.text(0.25, 0.48, "our margin over baseline (pentagon)\nthe largest the scoring allows", fontsize=10.5,
         color=MUTED, ha="center")
fig.text(0.5, 0.545, "1500/1500", fontsize=46, color=ACCENT, ha="center", fontweight="bold")
fig.text(0.5, 0.48, "cloud photographs showing\na correct answer", fontsize=10.5, color=MUTED, ha="center")
fig.text(0.75, 0.545, "5 knobs", fontsize=46, color=INK, ha="center", fontweight="bold")
fig.text(0.75, 0.48, "enough to reach 0.999 —\nfound in ~30 s on a laptop", fontsize=10.5,
         color=MUTED, ha="center")
bullets(fig, [
    "MIS is scheduling, spectrum allocation, portfolio screening — 'pick the most, no conflicts'.\nRydberg machines solve it natively: the constraint is physics, not code.",
    "Our contribution scales: a 5-knob sweep, trained once on a small graph, re-used across a graph\nfamily at zero cost — the exact recipe Challenge 03's 80-atom instances need.",
    "Pasqal stack credit: Pulser device models + judge's simulator, free-tier cloud for 500-shot\nvalidation, and the FRESNEL_CAN1 QPU + portal for the real-atom evidence in this deck.",
], y=0.36, dy=0.095, fs=12.5)
pdf.savefig(fig); plt.close(fig)

# ── 12 · score sheet ─────────────────────────────────────────────────────
fig = new_slide("Challenge 02 — the score sheet", "summary")
tbl = [
    ("", "star K₁,₃", "pentagon C₅", "duration"),
    ("Baseline (starter sweep)", "0.727", "0.657", "4000 ns"),
    ("Ours · GRAPE (optimal control)", "0.999998", "0.999999", "1000–2000 ns"),
    ("Ours · 5-knob simple sweep", "0.9962", "0.9994", "1000 ns"),
    ("Cloud, 500 shots each", "500/500", "500/500 + 500/500", "—"),
    ("Real QPU, 500 shots", "68.4% exact (7× runner-up)", "n/a (lattice)", "1000 ns"),
]
y = 0.72
for i, row in enumerate(tbl):
    bold = "bold" if i in (0, 2) else "normal"
    color = GOOD if i == 2 else INK
    for text, xx in zip(row, (0.06, 0.44, 0.62, 0.84)):
        fig.text(xx, y, text, fontsize=12.5, color=color, fontweight=bold)
    y -= 0.062
y -= 0.03
bullets(fig, [
    "Both puzzles beaten by +0.27 and +0.34 — the largest margins the scoring allows.",
    "Five equally-valid pentagon answers, sampled evenly — a visibly quantum result.",
    "Everything regenerates from the public repo: scorer, optimizer, figures, batch IDs.",
], y=y, dy=0.07, fs=13.5)
pdf.savefig(fig); plt.close(fig)

pdf.close()
print("wrote CH02_slides.pdf (12 slides)")
