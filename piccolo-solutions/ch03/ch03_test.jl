#!/usr/bin/env julia
# Quick timing test of Ch03 sparse ODE at N=20
using LinearAlgebra, OrdinaryDiffEq, SparseArrays, Printf, Random
Random.seed!(42)

const C6 = 865.723
const Ω_MAX = 0.012566
const Δ_MAX = 0.12566
const Δ_RANGE = 0.01257

N = 20
L = 30.0
positions = L * rand(2, N)

# Compute R_b and graph
R_b = (C6 * 1e3 / 6.283)^(1 / 6)
adj = zeros(Bool, N, N)
for i in 1:N, j in (i+1):N
    r = sqrt(sum((positions[:, i] - positions[:, j]) .^ 2))
    adj[i, j] = adj[j, i] = r < R_b
end
density = sum(adj) / (N*(N-1))
@printf("R_b=%.1fµm  edge_density=%.3f\n", R_b, density)

# Enumerate MIS (backtracking)
function enumerate_max_mis(adj)
    N = size(adj, 1)
    best_sets = Vector{Vector{Int}}()
    best_size = 0
    function backtrack(verts, candidates)
        if isempty(candidates)
            sz = length(verts)
            if sz > best_size
                best_size = sz
                empty!(best_sets); push!(best_sets, copy(verts))
            elseif sz == best_size
                push!(best_sets, copy(verts))
            end
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
        b = 0
        for v in vs; b |= 1 << (N - v); end
        push!(mis_bits, b)
    end
    return mis_bits, best_size
end

@printf("Enumerating MIS... ")
@time mis_bits, mis_size = enumerate_max_mis(adj)
@printf("|MIS| = %d  (%d configurations)\n", mis_size, length(mis_bits))

# Build operators
@printf("Building operators... ")
@time begin
    dim = 2^N
    I_ = Int[]; J_ = Int[]; V_ = Float64[]
    sizehint!(I_, N*dim); sizehint!(J_, N*dim); sizehint!(V_, N*dim)
    for b in 0:(dim-1)
        for i in 0:(N-1)
            push!(I_, b+1); push!(J_, xor(b, 1<<i)+1); push!(V_, 0.5)
        end
    end
    H_Ω = sparse(I_, J_, V_, dim, dim)
    H_Δ_diag = Float64[count_ones(b) for b in 0:(dim-1)]
    E_int = zeros(Float64, dim)
    V_mat = zeros(N, N)
    for i in 1:N, j in (i+1):N
        r = sqrt(sum((positions[:, i] - positions[:, j]) .^ 2))
        V_mat[i, j] = V_mat[j, i] = C6 / r^6
    end
    for b in 0:(dim-1)
        s = 0.0
        for i in 1:N, j in (i+1):N
            if V_mat[i, j] != 0
                s += V_mat[i,j] * ((b>>(N-i))&1) * ((b>>(N-j))&1)
            end
        end
        E_int[b+1] = s
    end
end

# Single evaluation (cold start)
T = 3000.0
@printf("Single ODE solve at N=%d, T=%.0fns...\n", N, T)
@time begin
    nk = 8
    Ω_k = [0.0, 0.006, 0.006, 0.006, 0.006, 0.006, 0.006, 0.0]
    Δ_k = [-Δ_RANGE, -0.008, 0.0, 0.005, 0.005, 0.008, Δ_RANGE, Δ_RANGE]
    knot_t = collect(range(0.0, T, length=nk))
    Ω_f = t -> begin i=clamp(searchsortedlast(knot_t,t),1,nk-1); f=(t-knot_t[i])/(knot_t[i+1]-knot_t[i]); Ω_k[i]+f*(Ω_k[i+1]-Ω_k[i]) end
    Δ_f = t -> begin i=clamp(searchsortedlast(knot_t,t),1,nk-1); f=(t-knot_t[i])/(knot_t[i+1]-knot_t[i]); Δ_k[i]+f*(Δ_k[i+1]-Δ_k[i]) end

    ψ0 = zeros(ComplexF64, dim); ψ0[1] = 1.0
    function h!(dψ, ψ, p, t)
        @. dψ = -(E_int - Δ_f(t)*H_Δ_diag)*im*ψ
        mul!(dψ, H_Ω, ψ, -im*Ω_f(t), 1.0)
    end
    prob = ODEProblem(h!, ψ0, (0.0, T))
    sol = solve(prob, Tsit5(); saveat=[T], abstol=1e-5, reltol=1e-3)
    ψ_f = sol.u[end]
    P = sum(abs2(ψ_f[b+1]) for b in mis_bits)
    @printf("  P_MIS = %.6f\n", P)
end

# Memory usage
@printf("H_Ω nonzeros: %d  dim: %d\n", nnz(H_Ω), dim)
@printf("Memory: H_Ω=%.1fMB  vectors=%.1fMB\n",
        (sizeof(H_Ω) / 1e6), (2*dim*8*2 / 1e6))
println("\nTiming test done.")
