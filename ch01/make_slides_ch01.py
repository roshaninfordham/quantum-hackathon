#!/usr/bin/env python3
"""Challenge 01 slide deck -> CH01_slides.pdf (16:9, matplotlib-rendered).

Every figure is the committed evidence PNG; every number matches the repo.
Regenerate: .venv/bin/python ch01/make_slides_ch01.py
"""

import json

import matplotlib
import numpy as np

matplotlib.use("Agg")
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

INK = "#16161d"
ACCENT = "#0f766e"
GOOD = "#15803d"
BAD = "#b91c1c"
MUTED = "#6b7280"
BG = "#fbfaf7"

W, H = 13.333, 7.5   # 16:9 inches


def new_slide(title, kicker=None):
    fig = plt.figure(figsize=(W, H))
    fig.patch.set_facecolor(BG)
    if kicker:
        fig.text(0.055, 0.945, kicker.upper(), fontsize=11, color=ACCENT,
                 fontweight="bold", family="monospace")
    fig.text(0.055, 0.865, title, fontsize=26, color=INK, fontweight="bold")
    fig.text(0.055, 0.032, "Team 6 · Harmoniqs x Pasqal x Microsoft · July 29 2026",
             fontsize=8, color=MUTED)
    fig.text(0.945, 0.032, "github.com/roshaninfordham/quantum-hackathon",
             fontsize=8, color=MUTED, ha="right")
    return fig


def bullets(fig, items, x=0.055, y=0.76, dy=0.072, fs=14, color=INK, wrap=None):
    for text in items:
        marker, body = ("", text)
        fig.text(x, y, "–", fontsize=fs, color=ACCENT, fontweight="bold")
        fig.text(x + 0.022, y, body, fontsize=fs, color=color, va="top",
                 linespacing=1.3)
        y -= dy + body.count("\n") * fs * 0.0024
    return y


def image_panel(fig, path, rect, caption=None):
    ax = fig.add_axes(rect)
    ax.imshow(mpimg.imread(path))
    ax.axis("off")
    if caption:
        fig.text(rect[0] + rect[2] / 2, rect[1] - 0.028, caption,
                 fontsize=9.5, color=MUTED, ha="center")
    return ax


_slide_no = [0]


def save(fig):
    """One slide -> PDF page + PNG fallback (GitHub always renders PNGs)."""
    _slide_no[0] += 1
    pdf.savefig(fig)
    import os
    os.makedirs("slides_png", exist_ok=True)
    fig.savefig(f"slides_png/slide_{_slide_no[0]:02d}.png", dpi=130,
                facecolor=fig.get_facecolor())
    plt.close(fig)


pdf = PdfPages("CH01_slides.pdf")

# ── 1 · title ────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(W, H)); fig.patch.set_facecolor(BG)
fig.text(0.5, 0.62, "Entangling two atoms\nwith one global laser pulse",
         fontsize=34, color=INK, fontweight="bold", ha="center", linespacing=1.3)
fig.text(0.5, 0.44, "Challenge 01 — solved, cloud-validated, run on the real quantum computer",
         fontsize=15, color=ACCENT, ha="center")
fig.text(0.5, 0.30, "Fidelity 0.9926 / 0.7500 (baseline)   →   1.000000 / 1.000000 (ours)\n"
                    "Real atoms: 89.4% of 500 shots entangled",
         fontsize=14, color=INK, ha="center", linespacing=1.6)
fig.text(0.5, 0.12, "Team 6 · A Real Quantum Hackathon · Harmoniqs x Pasqal x Microsoft",
         fontsize=11, color=MUTED, ha="center")
save(fig)

# ── 2 · the problem ─────────────────────────────────────────────────────
fig = new_slide("The problem, in one slide", "challenge 01")
bullets(fig, [
    "We are given two atoms, sitting 5.0 or 6.5 micrometers apart, and a single laser that shines on both at once — we cannot address them individually.",
    "Our goal is the Bell state |Ψ⁺⟩ = (|gr⟩ + |rg⟩)/√2 — exactly one atom excited, but shared between both. That is entanglement.",
    "We control only two things over time: the laser power Ω(t) and its frequency offset δ(t), within a 6000-nanosecond budget.",
    "We are scored on fidelity, F = |⟨Ψ⁺|ψ(T)⟩|², which measures how close our final state is to the goal — 1.0 means perfect.",
    "To succeed, we must beat the starter pulse at BOTH spacings, while staying inside the machine's published limits.",
], y=0.74, dy=0.105, fs=15)
fig.text(0.055, 0.16, "Physics we exploit: two nearby excited atoms repel (V = C₆/r⁶). "
         "Inside the blockade radius R_b ≈ 7.2 µm, double excitation is forbidden — "
         "that forbidden-ness is what creates entanglement.",
         fontsize=13, color=ACCENT, style="italic", wrap=True)
save(fig)

# ── 2b · the idea in one picture (newbie slide) ─────────────────────────
from matplotlib.patches import Circle, FancyArrow  # noqa: E402

fig = new_slide("The idea in one picture", "for everyone")
ax = fig.add_axes([0.04, 0.13, 0.55, 0.62])
ax.set_xlim(-1, 12); ax.set_ylim(-3, 3.4); ax.set_aspect("equal"); ax.axis("off")


def _atom(x, y, on, label=None):
    ax.add_patch(Circle((x, y), 0.45, facecolor="#22c55e" if on else "#cbd5e1",
                        edgecolor=INK, lw=1.4, zorder=3))
    ax.text(x, y, "ON" if on else "OFF", ha="center", va="center", fontsize=8,
            fontweight="bold", color="white" if on else MUTED, zorder=4)
    if label:
        ax.text(x, y - 0.95, label, ha="center", fontsize=9, color=INK)


# left: start
_atom(1.0, 1.5, False, "atom A"); _atom(3.2, 1.5, False, "atom B")
ax.add_patch(Circle((1.0, 1.5), 1.55, fill=False, ls="--", edgecolor=ACCENT, lw=1.1, alpha=0.7))
ax.add_patch(Circle((3.2, 1.5), 1.55, fill=False, ls="--", edgecolor=ACCENT, lw=1.1, alpha=0.7))
ax.text(2.1, 3.15, "start: both OFF", ha="center", fontsize=10, color=INK)
ax.add_patch(FancyArrow(4.9, 1.5, 1.4, 0, width=0.10, color=INK))
ax.text(5.6, 2.1, "laser\npulse", ha="center", fontsize=8.5, color=INK)
# right: the two options at once
_atom(7.6, 2.3, True); _atom(9.8, 2.3, False)
_atom(7.6, 0.4, False); _atom(9.8, 0.4, True)
ax.text(11.0, 2.3, "A ON, B OFF", fontsize=9, va="center", color=INK)
ax.text(11.0, 0.4, "A OFF, B ON", fontsize=9, va="center", color=INK)
ax.text(8.7, -1.0, "BOTH at the same time — that is entanglement",
        ha="center", fontsize=10.5, color=ACCENT, fontweight="bold")
ax.text(8.7, -1.8, "(like flipping two coins and getting HT + TH together)",
        ha="center", fontsize=9, color=MUTED)
ax.text(2.1, -1.4, "dashed circles: the blockade —\ncircles overlap, so BOTH ON\nis physically forbidden",
        ha="center", fontsize=9, color=ACCENT)
bullets(fig, [
    "Think of each atom as a light switch:\nground |g⟩ is OFF, Rydberg |r⟩ is ON.",
    "Atoms this close cannot both be ON —\nthat is the blockade. So the pulse can\nonly place ONE excitation, and it is\nshared between the two atoms.",
    "That shared, both-options-at-once\nstate is exactly the Bell state\nwe are scored on.",
], x=0.64, y=0.72, dy=0.13, fs=12.5)
save(fig)

# ── 3 · the baseline and the gap ─────────────────────────────────────────
fig = new_slide("The starter pulse works at one spacing, fails at the other", "the gap")
bullets(fig, [
    "The baseline is simple: constant power, Ω = 2π×1 MHz, for 352 nanoseconds, with no frequency shaping.",
    "At r₁ = 5.0 µm the blockade is strong — V over Ω is 8.8 — and it scores F = 0.9926. That is fine.",
    "But at r₂ = 6.5 µm the blockade is weak — V over Ω drops to 1.83 — and the score collapses to F = 0.75.",
    "So where does the missing 25% go? Into the forbidden |rr⟩ state: 22% leaks straight through the weak blockade.",
], y=0.74, dy=0.10, fs=15)
fig.text(0.055, 0.24, "One number — V/Ω, interaction over drive — explains the whole gap.\n"
         "V is fixed by the atom spacing. But Ω is OURS to choose.",
         fontsize=16, color=INK, fontweight="bold", linespacing=1.5)
save(fig)

# ── 4 · see the failure ──────────────────────────────────────────────────
fig = new_slide("Watch the baseline fail — then watch ours not", "evidence")
image_panel(fig, "fig_dynamics_r2.png", [0.06, 0.24, 0.88, 0.56],
            "x-axis: time during the pulse (µs) · y-axis: probability of each atomic configuration")
bullets(fig, [
    "On the left, the baseline: watch the red curve — the forbidden |rr⟩ state — fill up to 22%, while the green target stalls at 0.75.",
    "On the right, our pulse: the red curve stays pinned at zero the whole time, and the green target rises to 1.0.",
], y=0.155, dy=0.055, fs=12.5)
save(fig)

# ── 5 · the one-knob experiment ──────────────────────────────────────────
fig = new_slide("The fix is one knob: slow down to restore the blockade", "hypothesis test")
image_panel(fig, "fig_omega_sweep.png", [0.08, 0.15, 0.5, 0.62],
            "x-axis: blockade strength V/Ω (log) · y-axis: fidelity F")
bullets(fig, [
    "We ran the same square pulse and\nonly lowered Ω, lengthening the\npulse to keep a full rotation.",
    "Fidelity climbs steadily with V/Ω\nand crosses 0.99 near V/Ω ≈ 9.",
    "That became our design rule — and\nthe 6000-nanosecond budget makes it\nfree, since the baseline used only 352.",
    "On top of that we add smooth ramps,\nand a small detuning δ that cancels\nthe energy shift Ω²/2V.",
], x=0.62, y=0.74, dy=0.11, fs=12.5)
save(fig)

# ── 6 · main results ────────────────────────────────────────────────────
fig = new_slide("Result: both spacings beaten, validated on Pasqal Cloud", "results")
image_panel(fig, "ch01_results.png", [0.05, 0.13, 0.9, 0.65],
            "top: our pulse shapes (x: time; blue: power Ω, red: frequency δ) · "
            "bottom-left: fidelity bars vs baseline · bottom-right: cloud shots (dots) vs simulation (circles)")
fig.text(0.055, 0.795, "Every pulse here was validated by the device's own contract checker, then fired 500 times each on Pasqal Cloud.",
         fontsize=12.5, color=INK)
save(fig)

# ── 7 · robustness ───────────────────────────────────────────────────────
fig = new_slide("Bonus: one pulse that tolerates 30% spacing error", "product angle")
image_panel(fig, "fig_robustness.png", [0.08, 0.15, 0.5, 0.62],
            "x-axis: atom spacing r (µm) · y-axis: fidelity F of ONE fixed pulse")
bullets(fig, [
    "Real machines never place atoms perfectly.",
    "So we optimized one single waveform\nfor the worst case over the whole band.",
    "The blue curve is that fixed pulse: it\nholds F above 0.997 all the way\nfrom 5.0 to 6.5 micrometers.",
    "The grey curve is the baseline — it\ncollapses to 0.55 over the same range.",
    "One calibration instead of one per\ngeometry — that is the product story.",
], x=0.62, y=0.74, dy=0.098, fs=12.5)
save(fig)

# ── 8 · speed limit ─────────────────────────────────────────────────────
fig = new_slide("Then we asked: how fast can the best pulse be?", "quantum speed limit")
image_panel(fig, "fig_time_frontier.png", [0.05, 0.15, 0.62, 0.6],
            "left — x-axis: pulse duration (ns) · y-axis: error 1−F (log) · right — the winning waveforms")
bullets(fig, [
    "Theory sets a hard floor:\nT = π/(√2·Ω_max) = 177 ns.\nNo pulse can beat it.",
    "We reach F = 0.999999 at just\n224 ns at r₁ — only 25 ns\nabove that floor.",
    "At r₂ the weak blockade sets its own\nwall near 420 ns — a measured speed\nlimit, which is itself a result.",
    "And the whole frontier took 5.4 s\nof laptop compute — an exact 3-state\nmodel with analytic gradients.",
], x=0.70, y=0.72, dy=0.125, fs=12.5)
save(fig)

# ── 9 · noise flips the ranking ──────────────────────────────────────────
fig = new_slide("Under real noise, the ranking flips — shorter wins", "hardware realism")
rows = json.load(open("noise_ranking.json"))
ax = fig.add_axes([0.08, 0.16, 0.55, 0.58])
labels, noiseless, noisy = [], [], []
for r in rows:
    if r["r"] == 6.5:
        labels.append(r["label"].split(" @")[0])
        noiseless.append(r["F_noiseless"]); noisy.append(r["F_noisy"])
x = np.arange(len(labels)); w = 0.38
ax.bar(x - w/2, noiseless, w, color="#cbd5e1", label="noiseless emulator")
ax.bar(x + w/2, noisy, w, color=ACCENT, label="with decay + dephasing")
for xi in range(len(labels)):
    ax.text(xi + w/2, noisy[xi] + .015, f"{noisy[xi]:.2f}", ha="center", fontsize=9)
ax.set_xticks(x, labels, fontsize=10); ax.set_ylim(0, 1.1)
ax.set_ylabel("fidelity F at r₂ = 6.5 µm"); ax.legend(fontsize=9)
ax.set_title("x-axis: pulse design · y-axis: fidelity, without vs with noise", fontsize=10, color=MUTED)
bullets(fig, [
    "Dephasing accumulates with time —\nour long 2.7-microsecond pulse\nloses 0.27 of fidelity to it.",
    "The short 420-nanosecond pulse\nkeeps 0.93.",
    "So the design law is simple: pulse\nduration IS the noise coupling —\nminimize time first, then shape.",
    "That is exactly why we sent the\nshort, smooth pulse to the real machine.",
], x=0.68, y=0.70, dy=0.12, fs=12.5)
save(fig)

# ── 10 · real QPU: what the atoms answered ───────────────────────────────
fig = new_slide("500 shots on the real machine: 89.4% entangled", "real atoms · FRESNEL_CAN1")
image_panel(fig, "screenshots/pasqal_qpu_bitstrings.png", [0.04, 0.13, 0.56, 0.65],
            "Pasqal's own portal · x-axis: measured two-atom outcome · y-axis: % of 500 shots")
bullets(fig, [
    "The two tall bars ARE the Bell state:\n'01' at 46% plus '10' at 43% gives\n89.4% with exactly one atom excited.",
    "And they are equal within noise —\nthe symmetry physics demands,\ndelivered by the data.",
    "The '11' bar — a blockade violation —\nis just 2.4%: forbidden stayed forbidden.",
    "The '00' bar, at 8%, is readout and\ndecay — the exact error channel our\nnoise model predicted.",
    "We published the expected window\nbefore the run — and we hit it.",
], x=0.63, y=0.76, dy=0.095, fs=12)
save(fig)

# ── 11 · real QPU: the pulse the machine played ──────────────────────────
fig = new_slide("The machine's dashboard shows our physics back to us", "real atoms · the pulse")
image_panel(fig, "screenshots/pasqal_qpu_pulse.png", [0.04, 0.13, 0.56, 0.65],
            "Pasqal portal, Pulses tab · x-axis: time (ns) · purple: laser power Ω(t) · white: detuning δ(t)")
bullets(fig, [
    "This entire pulse is 260 nanoseconds,\nstart to finish.",
    "The power rises smoothly from zero,\nwith no jumps — the hardware-true\npulse our scientists asked for.",
    "Notice the label the portal itself puts\non the pulse: an area of 5π/7 ≈ 0.714π.",
    "Theory says a two-atom collective\nπ-pulse needs area π/√2 ≈ 0.707π.",
    "That is the √2 collective enhancement,\non the machine's own dashboard,\ncorrect to one percent.",
], x=0.63, y=0.76, dy=0.095, fs=12)
save(fig)

# ── 11b · how the score is computed ──────────────────────────────────────
fig = new_slide("How the score is computed — no magic", "the metric")
fig.text(0.5, 0.70, r"F  =  |⟨Ψ⁺| ψ(T)⟩|²", fontsize=40, color=INK,
         ha="center", fontweight="bold")
bullets(fig, [
    "Here ψ(T) is the state our pulse actually produced — for two atoms it is just four numbers, computed exactly.",
    "The bracket ⟨Ψ⁺|ψ(T)⟩ is the overlap with the perfect Bell state — it asks: how much of the ideal is in what we made?",
    "Squaring that overlap turns it into a probability: 1.000 means perfect, zero means nothing.",
    "On hardware there is no ψ to peek at — so the machine takes 500 photographs and we compare the\nfour outcome percentages against the simulation. Agreement within √(p(1−p)/500) ≈ ±2% = validated.",
], y=0.56, dy=0.095, fs=13.5)
fig.text(0.30, 0.185, "1.000000", fontsize=42, color=GOOD, ha="center", fontweight="bold")
fig.text(0.30, 0.125, "our best F, both spacings (simulation)", fontsize=11, color=MUTED, ha="center")
fig.text(0.70, 0.185, "89.4%", fontsize=42, color=ACCENT, ha="center", fontweight="bold")
fig.text(0.70, 0.125, "entangled shots on the real machine (500 photos)", fontsize=11, color=MUTED, ha="center")
save(fig)

# ── 11c · why it matters + the Pasqal stack ──────────────────────────────
fig = new_slide("Why this matters beyond the score", "commercial value")
bullets(fig, [
    "Entangling pairs is THE primitive: every neutral-atom algorithm, sensor, or network starts here.",
    "Our robust pulse holds F > 0.997 across a 30% spacing error — real machines misplace atoms,\nand a pulse that doesn't care means ONE calibration instead of one per geometry. That is uptime.",
    "Our fast pulses run 6–11× shorter — less exposure to noise means more of the error budget left\nfor the actual computation. Duration is money on quantum hardware.",
    "The whole design loop is seconds on a laptop — cheap enough to re-run at every calibration cycle.",
], y=0.74, dy=0.105, fs=13.5)
fig.text(0.055, 0.30, "Built on the Pasqal stack:", fontsize=13, color=INK, fontweight="bold")
bullets(fig, [
    "Pulser (open source) — the exact device model + the simulator the judges score with.",
    "Pasqal Cloud free emulator — 500-shot validation of every pulse before spending hardware budget.",
    "FRESNEL_CAN1 QPU — the real-atom runs; the portal's register/pulse/bitstring views made every\nresult inspectable by anyone (see the screenshots in this deck).",
], y=0.255, dy=0.062, fs=12)
save(fig)

# ── 12 · closing numbers ─────────────────────────────────────────────────
fig = new_slide("Challenge 01 — the score sheet", "summary")
tbl = [
    ("", "r₁ = 5.0 µm", "r₂ = 6.5 µm", "duration"),
    ("Baseline (starter pulse)", "0.9926", "0.7500", "352 ns"),
    ("v1 · simple analytic (4 params)", "0.99990", "0.99944", "~2400 ns"),
    ("v1r · one spacing-robust pulse", "0.99944", "0.99701", "2400 ns"),
    ("v2 · time-optimal (at the QSL)", "0.999999", "0.999998", "224 / 420 ns"),
    ("v3 · hardware-true smooth", "1.000000", "1.000000", "352 / 600 ns"),
]
y = 0.72
for i, row in enumerate(tbl):
    bold = "bold" if i in (0, 5) else "normal"
    color = INK if i != 5 else GOOD
    for text, xx, ww in zip(row, (0.06, 0.47, 0.63, 0.80), (None,)*4):
        fig.text(xx, y, text, fontsize=13.5, color=color, fontweight=bold)
    y -= 0.062
y -= 0.02
bullets(fig, [
    "Cloud: 7 pulses × 500 shots — every population within shot noise of prediction.",
    "Real QPU: P_bell = 0.894, inside the window we published BEFORE the run.",
    "Every number in this deck regenerates from the public repo in minutes.",
], y=y, dy=0.075, fs=14)
save(fig)

pdf.close()
print("wrote CH01_slides.pdf (12 slides)")
