#!/usr/bin/env julia
# Challenge 01 — Bell state preparation on 2 Rydberg atoms
# Maximize |⟨Ψ⁺|ψ(T)⟩|² at two spacings (r₁=5.0µm, r₂=6.5µm)
# Strategy: shape Ω(t) and Δ(t) via optimal control; at r₂ suppress |rr⟩ leakage

using Piccolo
using LinearAlgebra
using JLD2
using TOML
using Printf
using Random
Random.seed!(42)

# ── Constants (device envelope, rad/ns · ns · µm) ──────────────────────
const C6       = 865_723.0e-3        # rad/ns · µm⁶
const Ω_MAX    = 0.012566370614359172 # rad/ns (12.57 rad/µs)
const Δ_MAX    = 0.12566370614359172  # rad/ns (125.7 rad/µs)
const CLOCK_NS = 4.0                  # device clock period

# Spacings
const R1 = 5.0    # µm
const R2 = 6.5    # µm

# Interaction strengths at each spacing
V(r) = C6 / r^6
const V1 = V(R1)  # ≈ 0.0554 rad/ns (55.4 rad/µs)
const V2 = V(R2)  # ≈ 0.01148 rad/ns (11.48 rad/µs)

# Reference pulse: Ω_ref = 2π × 1.0 MHz = 6.283 rad/µs
const Ω_REF = 6.283e-3  # rad/ns
const T_REF = π / (√2 * Ω_REF)  # ≈ 354 ns

println("═══ Challenge 01 — Rydberg Bell State ═══")
println("  V1 = $(V1 * 1000) rad/µs, V1/Ω_ref = $(V1/Ω_REF)")
println("  V2 = $(V2 * 1000) rad/µs, V2/Ω_ref = $(V2/Ω_REF)")
println("  T_ref ≈ $(round(T_REF)) ns")
flush(stdout)

# ── Build system operators ─────────────────────────────────────────────
# Single-qubit operators
σx = ComplexF64[0 1; 1 0]
n  = ComplexF64[0 0; 0 1]   # |r⟩⟨r|
I2 = ComplexF64[1 0; 0 1]

# Embed in 2-atom space
σx_1 = kron(σx, I2)
σx_2 = kron(I2, σx)
n_1  = kron(n, I2)
n_2  = kron(I2, n)

# Drive operators (same for both spacings)
H_Ω = (σx_1 + σx_2) / 2      # Rabi drive: Ω(t) coefficient
H_Δ = -(n_1 + n_2)           # Detuning: Δ(t) coefficient

# Initial and target states (column vectors)
ψ0 = ComplexF64[1, 0, 0, 0]                       # |gg⟩
ψ_target = ComplexF64[0, 1/√2, 1/√2, 0] / norm(ComplexF64[0, 1/√2, 1/√2, 0])  # |Ψ⁺⟩

# ── Solve at one spacing ────────────────────────────────────────────────
function solve_at_spacing(r, V, label)
    println("\n─── Solving at r = $(r) µm ($label) ───")
    flush(stdout)

    # Build system with the correct interaction
    H_drift = V * kron(n, n)   # V · n₁n₂ = C₆/r⁶ · |rr⟩⟨rr|
    sys = QuantumSystem(H_drift, [H_Ω, H_Δ], [(0.0, Ω_MAX), (-Δ_MAX, Δ_MAX)])

    # Optimization parameters
    T = 500.0       # ns — more time for the optimizer at weak blockade
    N = 100         # timesteps (100 × 5ns = 500ns — not on 4ns clock but fine in sim)
    max_iter = 200

    # Initial guess: seeded with a resonant π-pulse area
    times = collect(range(0.0, T, length = N))
    Ω_init = fill(Ω_REF, 1, N)    # start near the reference amplitude
    Δ_init = zeros(1, N)           # start at zero detuning
    u_init = vcat(Ω_init, Δ_init)

    pulse = ZeroOrderPulse(u_init, times)

    # Ket trajectory for state preparation
    qtraj = KetTrajectory(sys, pulse, ψ0, ψ_target)
    qcp = SmoothPulseProblem(qtraj, N;
        piccolo_options = PiccoloOptions(timesteps_all_equal = true),
        Q = 100.0,
        R = 1e-4)

    # Solve
    solve!(qcp; max_iter = max_iter, print_level = 1,
           callback = Piccolo.Callbacks.callback_factory(
               (opt, st; kwargs...) -> begin
                   k = Int(st.iter_count)
                   if k % 10 == 0
                       @printf("  iter=%d f=%.6e inf_pr=%.3e inf_du=%.3e\n",
                               k, st.obj_value, st.inf_pr, st.inf_du)
                       flush(stdout)
                   end
                   return true
               end
           ))

    # Re-rollout verification (independent ODE solve)
    ψ_raw = ket_rollout(get_trajectory(qcp), sys)[:, end]
    d = length(ψ_target)
    ψ_final = ComplexF64[ψ_raw[i] + im * ψ_raw[i + d] for i in 1:d]
    F = abs2(dot(ψ_target, ψ_final))

    @printf("  >>> F = %.8f at r = %.1f µm\n", F, r)
    flush(stdout)

    return (F = F, sys = sys, qcp = qcp, ψ_final = ψ_final)
end

# ── Solve both spacings ─────────────────────────────────────────────────
result_1 = solve_at_spacing(R1, V1, "strong blockade")
result_2 = solve_at_spacing(R2, V2, "weak blockade")

# ── Reference fidelities ────────────────────────────────────────────────
# At r₁ (V/Ω_ref = 8.8): reference square pulse gives F ≈ 0.999+
# At r₂ (V/Ω_ref = 1.8): reference leaks to |rr⟩, F ≈ 0.97-0.98
println("\n═══ RESULTS ═══")
println("  r₁ = $(R1) µm: F = $(result_1.F)")
println("  r₂ = $(R2) µm: F = $(result_2.F)")
println("  Reference r₁: near-unity (strong blockade)")
println("  Reference r₂: ~0.97-0.98 (leakage to |rr⟩)")
flush(stdout)

# ── Save results ────────────────────────────────────────────────────────
JLD2.save("pulse_r1.jld2", "traj", get_trajectory(result_1.qcp),
          "F", result_1.F, "r", R1, "ψ_final", result_1.ψ_final)
JLD2.save("pulse_r2.jld2", "traj", get_trajectory(result_2.qcp),
          "F", result_2.F, "r", R2, "ψ_final", result_2.ψ_final)

println("\nDone.")
flush(stdout)
