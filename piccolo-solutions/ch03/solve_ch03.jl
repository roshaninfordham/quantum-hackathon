#!/usr/bin/env julia
# Ch03 — MIS at scale (N=20) with matrix-free H·ψ + Nelder-Mead
# Uses pair-iteration for H_Ω·ψ and diagonal vectors for H_Δ + V_ij.
# No sparse matrix construction — pure matrix-free O(N·2^N) per eval.

using LinearAlgebra, OrdinaryDiffEq, Printf, Random
Random.seed!(42)

const C6 = 865.723
const Ω_MAX = 0.012566
const Δ_MAX = 0.12566
const Δ_RANGE = 0.01257

println("═══ Challenge 03 — MIS at N=20 ═══")
flush(stdout)

# ── Graph ───────────────────────────────────────────────────────────────
N = 20
L = 30.0
positions = L * rand(2, N)
R_b = (C6 * 1e3 / 6.283)^(1 / 6)
adj = zeros(Bool, N, N)
for i in 1:N, j in (i+1):N
    r = sqrt(sum((positions[:, i] - positions[:, j]) .^ 2))
    adj[i, j] = adj[j, i] = r < R_b
end
@printf("N=%d  R_b=%.1fµm  dim=2^%d=%d  edge_density=%.3f\n", N, R_b, N, 2^N, sum(adj)/(N*(N-1)))
flush(stdout)

# ── MIS enumeration ─────────────────────────────────────────────────────
function enumerate_max_mis(adj)
    N = size(adj, 1)
    best_sets = Vector{Vector{Int}}()
    best_size = 0
    function backtrack(verts, candidates)
        if isempty(candidates)
            sz = length(verts)
            if sz > best_size
                best_size = sz; empty!(best_sets); push!(best_sets, copy(verts))
            elseif sz == best_size; push!(best_sets, copy(verts)); end
            return
        end
        if length(verts) + length(candidates) < best_size; return; end
        v = candidates[1]
        backtrack([verts; v], [u for u in candidates if u != v && !adj[v, u]])
        backtrack(verts, candidates[2:end])
    end
    backtrack(Int[], collect(1:N))
    mis_bits = Int[]
    for vs in best_sets
        b = 0; for v in vs; b |= 1 << (N - v); end; push!(mis_bits, b)
    end
    return mis_bits, best_size
end
@time begin
    mis_bits, mis_size = enumerate_max_mis(adj)
end
@printf("|MIS| = %d  (states: %d)\n", mis_size, length(mis_bits))
flush(stdout)

# ── Pre-compute diagonal operators ──────────────────────────────────────
@printf("Pre-computing operators... ")
flush(stdout)
@time begin
    dim = 2^N
    H_Δ_diag = Float64[count_ones(b) for b in 0:(dim-1)]
    V_mat = zeros(N, N)
    for i in 1:N, j in (i+1):N
        r = sqrt(sum((positions[:, i] - positions[:, j]) .^ 2))
        V_mat[i, j] = V_mat[j, i] = C6 / r^6
    end
    E_int = zeros(Float64, dim)
    for b in 0:(dim-1)
        s = 0.0
        for i in 1:N, j in (i+1):N
            if V_mat[i, j] != 0
                s += V_mat[i, j] * ((b >> (N-i)) & 1) * ((b >> (N-j)) & 1)
            end
        end
        E_int[b+1] = s
    end
    # Bit masks for each qubit (MSB-first: qubit i → bit N-i)
    bit_masks = [1 << (N - i) for i in 1:N]
end
@printf("  done\n")
flush(stdout)

# ── Matrix-free H·ψ via pair-iteration ──────────────────────────────────
function apply_H!(dψ::Vector{ComplexF64}, ψ::Vector{ComplexF64},
                  Ω::Float64, Δ::Float64,
                  E_int::Vector{Float64}, H_Δ_diag::Vector{Float64},
                  bit_masks::Vector{Int})
    dim = length(ψ)
    # Diagonal: (E_int - Δ·n) term (elementwise)
    @inbounds @simd for b in 1:dim
        dψ[b] = -im * (E_int[b] - Δ * H_Δ_diag[b]) * ψ[b]
    end
    # Off-diagonal: Ω/2 Σ σ^x via pair iteration (cache-friendly)
    factor = -im * Ω * 0.5
    @inbounds for mask in bit_masks
        step = 2 * mask
        for base in 0:step:(dim-1)
            for offset in 0:(mask-1)
                b  = base + offset + 1
                b2 = base + offset + mask + 1
                v_ψ2 = factor * ψ[b2]
                v_ψ1 = factor * ψ[b]
                dψ[b]  += v_ψ2
                dψ[b2] += v_ψ1
            end
        end
    end
    return nothing
end

# ── Sweep parameterization ──────────────────────────────────────────────
function make_drives(Ω_knots, Δ_knots, T)
    n = length(Ω_knots)
    knot_t = collect(range(0.0, T, length=n))
    return (
        Ω = t -> begin i=clamp(searchsortedlast(knot_t, t),1,n-1); f=(t-knot_t[i])/(knot_t[i+1]-knot_t[i]); Ω_knots[i]+f*(Ω_knots[i+1]-Ω_knots[i]) end,
        Δ = t -> begin i=clamp(searchsortedlast(knot_t, t),1,n-1); f=(t-knot_t[i])/(knot_t[i+1]-knot_t[i]); Δ_knots[i]+f*(Δ_knots[i+1]-Δ_knots[i]) end
    )
end

function make_sweep(params)
    a = 0.15; b = 1.0 - a
    Ω_knots = [0.0, [max(0.0, min(Ω_MAX, p)) for p in params[1:4]]..., 0.0]
    Δ_knots = [-Δ_RANGE, [-Δ_RANGE + b * p * 2 * Δ_RANGE for p in params[5:8]]..., Δ_RANGE]
    return Ω_knots, Δ_knots
end

# ── Evaluate P_MIS ──────────────────────────────────────────────────────
function eval_pmis(params; T=3000.0, verbose=false)
    Ω_knots, Δ_knots = make_sweep(params)
    drives = make_drives(Ω_knots, Δ_knots, T)

    ψ = zeros(ComplexF64, dim)
    ψ[1] = 1.0 + 0.0im
    dψ = similar(ψ)
    tmp = similar(ψ)

    function ode_f!(dψ, ψ, p, t)
        apply_H!(dψ, ψ, drives.Ω(t), drives.Δ(t), E_int, H_Δ_diag, bit_masks)
    end

    prob = ODEProblem(ode_f!, ψ, (0.0, T))
    sol = solve(prob, Tsit5(); saveat=[T], abstol=1e-5, reltol=1e-3)
    ψ_f = sol.u[end]

    P = sum(abs2(ψ_f[b+1]) for b in mis_bits)
    return P
end

# ── Nelder-Mead ─────────────────────────────────────────────────────────
n_par = 8
x0 = [0.006, 0.006, 0.006, 0.006, 0.25, 0.5, 0.75, 0.9]

@printf("Initial evaluation... ")
flush(stdout)
@time P0 = eval_pmis(x0)
@printf("  P_MIS(initial) = %.6f\n", P0)
flush(stdout)

α, γ, ρ, σ = 1.0, 2.0, 0.5, 0.5
S = [copy(x0) for _ in 1:n_par+1]
for i in 1:n_par
    S[i+1][i] += 0.2 * (abs(x0[i]) > 0.01 ? abs(x0[i]) : 0.2)
end
y = [-eval_pmis(S[i]) for i in 1:n_par+1]
best_val = -typemax(Float64)
max_iter = 200

log_file = open("ch03_optimize.log", "w")
@printf(log_file, "Ch03 Nelder-Mead at N=%d, dim=%d\n", N, dim)
flush(log_file)

for iter in 1:max_iter
    perm = sortperm(y)
    Sp, yp = S[perm], y[perm]
    if yp[1] < best_val
        best_val = yp[1]
        best_x = copy(Sp[1])
        @printf("  iter=%d best P_MIS=%.6f\n", iter, -best_val)
        @printf(log_file, "iter=%d best P_MIS=%.6f x=%s\n", iter, -best_val, join(round.(best_x, digits=6), " "))
        flush(log_file)
        flush(stdout)
    end
    if yp[end] - yp[1] < 1e-6 * (1 + abs(yp[1]))
        @printf("  Converged at iter=%d\n", iter); break
    end
    xbar = sum(Sp[1:n_par]) / n_par
    xr = xbar + α * (xbar - Sp[end])
    yr = -eval_pmis(xr)
    if yp[1] ≤ yr < yp[end-1]
        Sp[end] = xr; yp[end] = yr
    elseif yr < yp[1]
        xe = xbar + γ * (xr - xbar); ye = -eval_pmis(xe)
        if ye < yr; Sp[end] = xe; yp[end] = ye
        else; Sp[end] = xr; yp[end] = yr; end
    else
        if yr < yp[end]
            xc = xbar + ρ * (xr - xbar); yc = -eval_pmis(xc)
            if yc < yr; Sp[end] = xc; yp[end] = yc
            else; for i in 2:n_par+1; Sp[i] = Sp[1] + σ * (Sp[i] - Sp[1]); yp[i] = -eval_pmis(Sp[i]); end; end
        else
            xc = xbar - ρ * (xbar - Sp[end]); yc = -eval_pmis(xc)
            if yc < yp[end]; Sp[end] = xc; yp[end] = yc
            else; for i in 2:n_par+1; Sp[i] = Sp[1] + σ * (Sp[i] - Sp[1]); yp[i] = -eval_pmis(Sp[i]); end; end
        end
    end
    S, y = Sp, yp
end

perm = sortperm(y)
x_best = S[perm[1]]
Ω_k, Δ_k = make_sweep(x_best)
P_best = -y[perm[1]]

println("\n════════════════════════════════════")
@printf("★★★ Ch03 RESULT ★★★\n")
@printf("P_MIS = %.8f\n", P_best)
@printf("Ω knots = %s\n", join(round.(Ω_k, digits=6), "  "))
@printf("Δ knots = %s\n", join(round.(Δ_k, digits=6), "  "))
println("════════════════════════════════════")

@printf(log_file, "\nFINAL P_MIS = %.8f\nΩ = %s\nΔ = %s\n", P_best,
        join(round.(Ω_k, digits=6), " "), join(round.(Δ_k, digits=6), " "))
close(log_file)

# Save graph + result
open("ch03_result.toml", "w") do io
    println(io, "N=", N); println(io, "dim=", dim)
    println(io, "P_MIS=", P_best); println(io, "mis_size=", mis_size)
    println(io, "n_mis_states=", length(mis_bits))
    println(io, "\npositions = [")
    for i in 1:N; println(io, "  [", positions[1,i], ", ", positions[2,i], "],"); end
    println(io, "]")
end

println("Done. log in ch03_optimize.log, result in ch03_result.toml")
