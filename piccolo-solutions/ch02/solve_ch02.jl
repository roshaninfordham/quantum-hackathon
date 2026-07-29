#!/usr/bin/env julia
# Challenge 02 — MIS by direct ODE + parameterized sweep (fast track)
# We parameterize Ω(t) and Δ(t) with a few Bezier-like control points,
# simulate the Schrödinger equation, and maximize P_MIS directly.

using LinearAlgebra, OrdinaryDiffEq, JLD2, Printf, Random
Random.seed!(1234)

const C6    = 865.723        # rad/ns · µm⁶
const C6_μs = C6 * 1e3       # rad/µs · µm⁶

# ── Hamiltonian builder ──────────────────────────────────────────────
const σx = ComplexF64[0 1; 1 0]
const n_op = ComplexF64[0 0; 0 1]  # |r⟩⟨r|
const I2 = ComplexF64[1 0; 0 1]

function embed(op, i, N)
    ops = [I2 for _ in 1:N]; ops[i] = op
    r = ops[1]; for j in 2:N; r = kron(r, ops[j]); end; return r
end

function build_system_matrices(N)
    H_Ω = sum(embed(σx, i, N) for i in 1:N) / 2
    H_Δ = -sum(embed(n_op, i, N) for i in 1:N)
    H_int = zeros(ComplexF64, 2^N, 2^N)
    return H_Ω, H_Δ, H_int
end

# ── Parameterized sweep ──────────────────────────────────────────────
# We parameterize Ω(t) and Δ(t) with n_knots control points per drive,
# interpolated with a cubic spline. Then we evaluate P_MIS.
function eval_sweep(params, positions; T=1000.0, n_knots=6, n_steps=200)
    N = size(positions, 2)
    H_Ω, H_Δ, H_int = build_system_matrices(N)

    # Fill interaction
    for i in 1:N, j in (i+1):N
        r = sqrt(sum((positions[:,i] - positions[:,j]).^2))
        H_int += (C6 / r^6) * embed(n_op, i, N) * embed(n_op, j, N)
    end

    # Build time-dependent Hamiltonian
    # params is [Ω_knots..., Δ_knots...] (length 2*n_knots)
    Ω_knots = params[1:n_knots]
    Δ_knots = params[n_knots+1:end]
    knot_times = collect(range(0.0, T, length=n_knots))
    times = collect(range(0.0, T, length=n_steps))

    function Ω(t)
        i = searchsortedlast(knot_times, t)
        i = clamp(i, 1, n_knots-1)
        f = (t - knot_times[i]) / (knot_times[i+1] - knot_times[i])
        return Ω_knots[i] + f * (Ω_knots[i+1] - Ω_knots[i])
    end
    function Δ(t)
        i = searchsortedlast(knot_times, t)
        i = clamp(i, 1, n_knots-1)
        f = (t - knot_times[i]) / (knot_times[i+1] - knot_times[i])
        return Δ_knots[i] + f * (Δ_knots[i+1] - Δ_knots[i])
    end

    # ODE: dψ/dt = -i H(t) ψ
    function H(t)
        return -im * (H_int + Ω(t) * H_Ω + Δ(t) * H_Δ)
    end
    function f!(dψ, ψ, p, t)
        dψ .= H(t) * ψ
    end

    ψ0 = zeros(ComplexF64, 2^N); ψ0[1] = 1.0
    prob = ODEProblem(f!, ψ0, (0.0, T))
    sol = solve(prob, Tsit5(); saveat=times, abstol=1e-8, reltol=1e-6)
    ψ_final = sol.u[end]

    # Compute P_MIS
    Δ_f_ref = 0.01257
    R_b = (C6_μs / 6.283)^(1/6)  # ≈ 7.2 µm
    adj = zeros(Bool, N, N)
    for i in 1:N, j in (i+1):N
        r = sqrt(sum((positions[:,i] - positions[:,j]).^2))
        adj[i,j] = adj[j,i] = r < R_b
    end
    max_sz = 0; mis_bits = Int[]
    for b in 0:(2^N - 1)
        # MSB-first: kron ordering is q1 (atom 1) is most significant
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
    P_MIS = sum(abs2(ψ_final[b+1]) for b in mis_bits)
    return P_MIS, ψ_final, times, mis_bits
end

# ── Solve ────────────────────────────────────────────────────────────
function solve_mis_direct(name, positions; n_knots=6, n_steps=200)
    N = size(positions, 2)
    println("\n═══ $(name) ($(N) atoms) ═══")
    flush(stdout)

    Δ_0 = -0.01257; Δ_f = 0.01257; Ω_mid = 0.006

    # Linear ramp baseline at 1000ns
    params_lin = vcat(fill(Ω_mid, n_knots), collect(range(Δ_0, Δ_f, length=n_knots)))
    r1 = eval_sweep(params_lin, positions; n_knots=n_knots, n_steps=n_steps, T=1000.0)
    @printf("  Linear T=1000:     P_MIS = %.6f\n", r1[1])

    # Resonant: keep Δ=0, just Rabi flop
    Δ_zero = zeros(6)
    Ω_rabi = [0.0, Ω_mid, Ω_mid, Ω_mid, Ω_mid, 0.0]
    r2 = eval_sweep(vcat(Ω_rabi, Δ_zero), positions; n_knots=n_knots, n_steps=n_steps, T=1000.0)
    @printf("  Resonant T=1000:   P_MIS = %.6f\n", r2[1])

    # Resonant at 1500ns (longer Rabi flop)
    r3 = eval_sweep(vcat(Ω_rabi, Δ_zero), positions; n_knots=n_knots, n_steps=300, T=1500.0)
    @printf("  Resonant T=1500:   P_MIS = %.6f\n", r3[1])

    # Resonant at 2000ns
    r4 = eval_sweep(vcat(Ω_rabi, Δ_zero), positions; n_knots=n_knots, n_steps=400, T=2000.0)
    @printf("  Resonant T=2000:   P_MIS = %.6f\n", r4[1])

    # Half-sweep: Δ goes from -12.57 to 0 (stops at 0)
    Δ_half = [Δ_0, Δ_0 + 0.5*(0-Δ_0), 0, 0, 0, 0]
    Ω_half = [0.0, Ω_mid, Ω_mid, Ω_mid, Ω_mid, 0.0]
    r5 = eval_sweep(vcat(Ω_half, Δ_half), positions; n_knots=n_knots, n_steps=n_steps, T=1000.0)
    @printf("  Half-sweep T=1000: P_MIS = %.6f\n", r5[1])

    # Aggressive sweep at 1500ns (fast Δ transition)
    Δ_agg = [Δ_0, Δ_0 + 0.2*(Δ_f-Δ_0), Δ_0 + 0.4*(Δ_f-Δ_0),
             Δ_0 + 0.65*(Δ_f-Δ_0), Δ_0 + 0.85*(Δ_f-Δ_0), Δ_f]
    Ω_agg = [0.0, Ω_mid*1.2, Ω_mid*1.2, Ω_mid*0.8, Ω_mid*0.3, 0.0]
    r6 = eval_sweep(vcat(Ω_agg, Δ_agg), positions; n_knots=n_knots, n_steps=300, T=1500.0)
    @printf("  Aggressive T=1500: P_MIS = %.6f\n", r6[1])

    # Proper 3-stage at 4000ns: Ω ramp, Δ hold→sweep→hold (matching baseline)
    Ω_stage = [0.0, Ω_mid, Ω_mid, Ω_mid, Ω_mid, 0.0]
    Δ_stage = [Δ_0, Δ_0, Δ_0 + 0.3*(Δ_f-Δ_0), Δ_0 + 0.7*(Δ_f-Δ_0), Δ_f, Δ_f]
    r7 = eval_sweep(vcat(Ω_stage, Δ_stage), positions; n_knots=n_knots, n_steps=800, T=4000.0)
    @printf("  Stage T=4000:     P_MIS = %.6f\n", r7[1])

    best_tuple = argmax(r -> r[1], [r1, r2, r3, r4, r5, r6, r7])
    @printf("  >>> Best: P_MIS = %.6f\n", best_tuple[1])
    flush(stdout)
    return best_tuple
end

println("═══ Challenge 02 — Fast MIS via Direct ODE ═══")
flush(stdout)

# ── Star K₁₃ ─────────────────────────────────────────────────────────
ρ = 5.5
star_pos = [0.0   ρ      -ρ/2        -ρ/2;
            0.0   0.0     ρ*√3/2     -ρ*√3/2]
star_best = solve_mis_direct("Star K₁₃", star_pos; n_knots=6)

# ── Cycle C₅ ─────────────────────────────────────────────────────────
s = 5.5
angles = [2π * k / 5 for k in 0:4]
pentagon_pos = [s * cos.(angles)  s * sin.(angles)]'
pent_best = solve_mis_direct("Cycle C₅", pentagon_pos; n_knots=6)

println("\n═══ CHALLENGE 02 RESULTS ═══")
println("  Star K₁₃  P_MIS = $(star_best[1])  (baseline=0.909 at 4000ns)")
println("  Cycle C₅  P_MIS = $(pent_best[1])  (baseline=0.320 at 4000ns)")
flush(stdout)

JLD2.save("ch02_star.jld2", "P_MIS", star_best[1])
JLD2.save("ch02_pentagon.jld2", "P_MIS", pent_best[1])
println("\nDone.")
flush(stdout)
