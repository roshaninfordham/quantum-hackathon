#!/usr/bin/env julia
# Bare-metal fixed-step RK4 for N=20 MIS — no OrdinaryDiffEq overhead
using LinearAlgebra, Printf, Random
Random.seed!(42)

const C6 = 865.723; const Δ_RANGE = 0.01257

N = 20; L = 30.0
positions = L * rand(2, N)
dim = 2^N

# diag operators
H_Δ_diag = Float64[count_ones(b) for b in 0:(dim-1)]
V_mat = zeros(N, N)
for i in 1:N, j in (i+1):N
    r = sqrt(sum((positions[:,i] - positions[:,j]) .^ 2))
    V_mat[i,j] = V_mat[j,i] = C6 / r^6
end
E_int = zeros(Float64, dim)
for b in 0:(dim-1)
    s = 0.0
    for i in 1:N, j in (i+1):N
        V_mat[i,j] != 0 && (s += V_mat[i,j] * ((b>>(N-i))&1) * ((b>>(N-j))&1))
    end
    E_int[b+1] = s
end
bit_masks = [1 << (N-i) for i in 1:N]

# Matrix-free H·ψ
function apply_H!(dψ, ψ, Ω, Δ)
    @inbounds for b in 1:dim
        dψ[b] = -im * (E_int[b] - Δ * H_Δ_diag[b]) * ψ[b]
    end
    factor = -im * Ω * 0.5
    @inbounds for mask in bit_masks
        for b in 0:(dim-1)
            dψ[b+1] += factor * ψ[xor(b, mask) + 1]
        end
    end
end

# Evaluate P_MIS
function eval_pmis(Ω_k, Δ_k; T=3000.0, dt=10.0)
    nk = length(Ω_k)
    knot_t = collect(range(0.0, T, length=nk))
    n_steps = Int(round(T / dt)) + 1
    dt_actual = T / (n_steps - 1)

    ψ = zeros(ComplexF64, dim); ψ[1] = 1.0
    k1 = similar(ψ); k2 = similar(ψ); k3 = similar(ψ); k4 = similar(ψ); tmp = similar(ψ)

    for step in 0:(n_steps-2)
        t = step * dt_actual
        i = clamp(searchsortedlast(knot_t, t), 1, nk-1)
        f = (t - knot_t[i]) / (knot_t[i+1] - knot_t[i])
        Ω_t = Ω_k[i] + f * (Ω_k[i+1] - Ω_k[i])
        Δ_t = Δ_k[i] + f * (Δ_k[i+1] - Δ_k[i])
        # Inline RK4 to avoid closure allocation
        h = dt_actual; h2 = 0.5*h; h6 = h/6.0
        apply_H!(k1, ψ, Ω_t, Δ_t)
        @inbounds for i in 1:dim; tmp[i] = ψ[i] + h2 * k1[i]; end
        apply_H!(k2, tmp, Ω_t, Δ_t)  # mid-step: same Ω,Δ for simplicity
        @inbounds for i in 1:dim; tmp[i] = ψ[i] + h2 * k2[i]; end
        apply_H!(k3, tmp, Ω_t, Δ_t)
        @inbounds for i in 1:dim; tmp[i] = ψ[i] + h * k3[i]; end
        apply_H!(k4, tmp, Ω_t, Δ_t)
        @inbounds for i in 1:dim
            ψ[i] += h6 * (k1[i] + 2k2[i] + 2k3[i] + k4[i])
        end
    end

    # P_MIS from full state
    P = 0.0
    @inbounds for b in mis_bits
        P += abs2(ψ[b+1])
    end
    return P
end

# MIS enumeration
function enumerate_max_mis(adj)
    N = size(adj, 1)
    best_sets = Vector{Vector{Int}}()
    best_size = 0
    function backtrack(verts, candidates)
        if isempty(candidates)
            sz = length(verts)
            if sz > best_size; best_size = sz; empty!(best_sets); push!(best_sets, copy(verts))
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
    for vs in best_sets; b=0; for v in vs; b |= 1 << (N-v); end; push!(mis_bits, b); end
    return mis_bits, best_size
end

# Build adjacency
R_b = (C6 * 1e3 / 6.283)^(1 / 6)
adj = zeros(Bool, N, N)
for i in 1:N, j in (i+1):N
    r = sqrt(sum((positions[:,i] - positions[:,j]) .^ 2))
    adj[i,j] = adj[j,i] = r < R_b
end
@printf("N=%d R_b=%.1f dim=%d\n", N, R_b, dim)

mis_bits, mis_size = enumerate_max_mis(adj)
@printf("|MIS|=%d (%d states)\n", mis_size, length(mis_bits))

# Warm-up
@printf("Warm-up eval... "); flush(stdout)
GC.gc()
@time begin
    P0 = eval_pmis([0.0,0.006,0.006,0.006,0.006,0.006,0.006,0.0],
                   [-Δ_RANGE,-0.008,0.0,0.005,0.005,0.008,Δ_RANGE,Δ_RANGE])
end
@printf("  P_MIS=%.6f\n", P0); flush(stdout)

# Timed eval (post-compilation)
@printf("Timed eval... "); flush(stdout)
GC.gc()
@time begin
    P1 = eval_pmis([0.0,0.005,0.007,0.004,0.006,0.006,0.005,0.0],
                   [-Δ_RANGE,-0.005,0.002,0.008,0.006,0.010,Δ_RANGE,Δ_RANGE])
end
@printf("  P_MIS=%.6f\n", P1); flush(stdout)

# Multiple evals (simulate Nelder-Mead cost)
@printf("Batch of 10 evals... "); flush(stdout)
GC.gc()
@time begin
    for _ in 1:10
        eval_pmis([0.0,0.005,0.007,0.004,0.006,0.006,0.005,0.0],
                   [-Δ_RANGE,-0.005,0.002,0.008,0.006,0.010,Δ_RANGE,Δ_RANGE])
    end
end
@printf("  done\n"); flush(stdout)
