#!/usr/bin/env julia
# Challenge 02 — MIS via optimal control (Piccolo)
# Shape Ω(t) and Δ(t) to maximize P_MIS population on embedded graphs.
# Uses the same apparatus as Ch01: QuantumSystem + KetTrajectory + Ipopt.

using Piccolo
using LinearAlgebra, JLD2, Printf, Random
Random.seed!(42)

const C6    = 865_723.0e-3        # rad/ns · µm⁶
const Ω_MAX = 0.012566370614359172 # rad/ns (12.57 rad/µs)
const Δ_MAX = 0.12566370614359172  # rad/ns (125.7 rad/µs)

# 2-level atom: |g⟩ (=|0⟩), |r⟩ (=Rydberg)
σx = ComplexF64[0 1; 1 0]    # |g⟩⟨r| + |r⟩⟨g|
n  = ComplexF64[0 0; 0 1]    # |r⟩⟨r|
I2 = ComplexF64[1 0; 0 1]

function embed(op, i, N)
    ops = [I2 for _ in 1:N]; ops[i] = op
    return foldl(kron, ops)
end

function build_mis_system(positions)
    N = size(positions, 2)
    H_Ω  = sum(embed(σx, i, N) for i in 1:N) / 2
    H_Δ  = sum(embed(n,  i, N) for i in 1:N)
    H_int = zeros(ComplexF64, 2^N, 2^N)
    for i in 1:N, j in (i+1):N
        r = sqrt(sum((positions[:,i] - positions[:,j]).^2))
        H_int += (C6 / r^6) * embed(n, i, N) * embed(n, j, N)
    end
    return H_int, H_Ω, H_Δ
end

# ── MIS target state ───────────────────────────────────────────────────
function mis_subspace_indices(positions)
    N = size(positions, 2)
    R_b = 7.2  # µm — Blockade radius
    adj = zeros(Bool, N, N)
    for i in 1:N, j in (i+1):N
        r = sqrt(sum((positions[:,i] - positions[:,j]).^2))
        adj[i,j] = adj[j,i] = r < R_b
    end
    max_sz = 0; mis_bits = Int[]
    for b in 0:(2^N - 1)
        bits = [(b >> (N-1-k)) & 1 for k in 0:N-1]
        ok = true
        for i in 1:N, j in (i+1):N
            if bits[i]==1 && bits[j]==1 && adj[i,j]; ok=false; break; end
        end
        if !ok; continue; end
        sz = sum(bits)
        if sz > max_sz; max_sz = sz; mis_bits = [b]
        elseif sz == max_sz; push!(mis_bits, b); end
    end
    return mis_bits, max_sz
end

function mis_target_state(positions, pick_index=1)
    mis_bits, _ = mis_subspace_indices(positions)
    b = mis_bits[pick_index]
    N = size(positions, 2)
    ψ = zeros(ComplexF64, 2^N)
    ψ[b + 1] = 1.0
    return ψ, mis_bits
end

# ── Solve with Piccolo ─────────────────────────────────────────────────
function solve_mis_piccolo(name, positions; T=1000.0, N_steps=100, max_iter=200,
                           Ω0=Ω_MAX/2, label="")
    N = size(positions, 2)
    H_int, H_Ω, H_Δ = build_mis_system(positions)
    ψ0 = zeros(ComplexF64, 2^N); ψ0[1] = 1.0  # |0…0⟩

    ψ_target, mis_bits = mis_target_state(positions, 1)
    @printf("  %s N=%d dim=%d |MIS|=%d target_bit=0x%02x\n",
            label, N, 2^N, length(mis_bits), mis_bits[1])
    flush(stdout)

    # QuantumSystem with drift (blockade) and two drives (Ω, Δ)
    sys = QuantumSystem(H_int, [H_Ω, H_Δ], [(0.0, Ω_MAX), (-Δ_MAX, Δ_MAX)])

    # Initial guess: smooth turn-on at Ω0, linear Δ sweep
    times = collect(range(0.0, T, length=N_steps))
    Ω_init = Ω0 * abs2.(sin.(π * (times ./ T)))   # smooth rise/fall
    Δ_init = range(-Δ_MAX/10, Δ_MAX/10, length=N_steps)  # modest sweep
    u_init = vcat(Ω_init', Δ_init')
    pulse = ZeroOrderPulse(u_init, times)

    qtraj = KetTrajectory(sys, pulse, ψ0, ψ_target)
    qcp = SmoothPulseProblem(qtraj, N_steps;
        piccolo_options = PiccoloOptions(timesteps_all_equal = true),
        Q = 100.0, R = 1e-4)

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

    # ── Re-rollout verification ──────────────────────────────────────────
    ψ_raw = ket_rollout(get_trajectory(qcp), sys)[:, end]
    d = length(ψ_target)
    ψ_final = ComplexF64[ψ_raw[i] + im * ψ_raw[i + d] for i in 1:d]

    # P_MIS = sum over all MIS states
    P_MIS = sum(abs2(ψ_final[b+1]) for b in mis_bits)
    F_target = abs2(dot(ψ_target, ψ_final))

    @printf("  >>> P_MIS = %.8f  (to target state: F = %.8f)\n", P_MIS, F_target)
    flush(stdout)
    return (P_MIS = P_MIS, F_target = F_target, ψ_final = ψ_final, mis_bits = mis_bits)
end

# ═══════════════════════════════════════════════════════════════════════
println("═══ Challenge 02 — MIS via Piccolo Optimal Control ═══")
flush(stdout)

# ── Star K₁₃ ──────────────────────────────────────────────────────────
ρ = 5.5
star_pos = [0.0   ρ      -ρ/2        -ρ/2;
            0.0   0.0     ρ*√3/2     -ρ*√3/2]

star_res = solve_mis_piccolo("Star K₁₃", star_pos;
    T=1000.0, N_steps=100, max_iter=300, Ω0=6.283e-3, label="star")

# ── Cycle C₅ ──────────────────────────────────────────────────────────
s = 5.5
angles = [2π * k / 5 for k in 0:4]
pentagon_pos = [s * cos.(angles)  s * sin.(angles)]'

pent_res = solve_mis_piccolo("Cycle C₅", pentagon_pos;
    T=1000.0, N_steps=100, max_iter=300, Ω0=6.283e-3, label="pent")

# ═══════════════════════════════════════════════════════════════════════
println("\n═══ CHALLENGE 02 RESULTS ═══")
println("  Star K₁₃  P_MIS = $(star_res.P_MIS)")
println("  Cycle C₅  P_MIS = $(pent_res.P_MIS)")
println("\n  Baseline (4000ns linear ramp):")
println("    Star:  P_MIS = 0.909")
println("    Pent:  P_MIS = 0.320")
flush(stdout)

JLD2.save("ch02_star.jld2", "P_MIS", star_res.P_MIS, "ψ_final", star_res.ψ_final)
JLD2.save("ch02_pentagon.jld2", "P_MIS", pent_res.P_MIS, "ψ_final", pent_res.ψ_final)
println("\nDone.")
flush(stdout)
