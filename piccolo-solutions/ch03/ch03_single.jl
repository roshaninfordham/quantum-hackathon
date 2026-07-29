#!/usr/bin/env julia
# Single eval: does the default sweep beat the adiabatic benchmark?
using LinearAlgebra, SparseArrays, Printf, Random
Random.seed!(42)

const C6 = 865.723; const Ω_MAX = 0.012566; const Δ_RANGE = 0.01257

N = 20; L = 30.0
positions = L * rand(2, N)
dim = 2^N
@printf("N=%d dim=%d\n", N, dim); flush(stdout)

# diag ops
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

# Build H_Ω
@printf("Building H_Ω... "); flush(stdout)
@time begin
    nnz_total = dim * N
    colptr = Vector{Int}(undef, dim + 1)
    rowval = Vector{Int}(undef, nnz_total)
    nzval = Vector{Float64}(undef, nnz_total)
    for i in 1:dim+1; colptr[i] = (i-1) * N + 1; end
    for b in 0:(dim-1)
        base = b * N
        @inbounds for (j, mask) in enumerate(bit_masks)
            rowval[base + j] = xor(b, mask) + 1
            nzval[base + j] = 0.5
        end
    end
    H_Ω = SparseMatrixCSC(dim, dim, colptr, rowval, nzval)
end; flush(stdout)

function apply_H!(dψ, ψ, Ω, Δ)
    @inbounds @simd for b in 1:dim
        dψ[b] = -im * (E_int[b] - Δ * H_Δ_diag[b]) * ψ[b]
    end
    mul!(dψ, H_Ω, ψ, -im * Ω, one(ComplexF64))
end

# MIS enumeration
adj = zeros(Bool, N, N)
for i in 1:N, j in (i+1):N
    r = sqrt(sum((positions[:,i] - positions[:,j]) .^ 2))
    adj[i,j] = adj[j,i] = r < (C6 * 1e3 / 6.283)^(1/6)
end
function enumerate_max_mis(adj)
    N = size(adj,1); best_sets = Vector{Vector{Int}}(); best_size=0
    function backtrack(verts,candidates)
        if isempty(candidates)
            sz=length(verts)
            if sz>best_size; best_size=sz; empty!(best_sets); push!(best_sets,copy(verts))
            elseif sz==best_size; push!(best_sets,copy(verts)); end; return end
        if length(verts)+length(candidates)<best_size; return; end
        v=candidates[1]
        backtrack([verts;v],[u for u in candidates if u!=v&&!adj[v,u]])
        backtrack(verts,candidates[2:end])
    end; backtrack(Int[],collect(1:N))
    return [begin b=0; for v in vs; b|=1<<(N-v); end; b end for vs in best_sets]
end
mis_bits = enumerate_max_mis(adj)
@printf("|MIS|=%d (%d states)\n", maximum(count_ones.(b) for b in mis_bits), length(mis_bits))

# Evaluate a default sweep
function eval_sweep(Ω_knots, Δ_knots; T=2000.0, dt=10.0)
    nk=length(Ω_knots); knot_t=collect(range(0.0,T,length=nk))
    n_steps = Int(round(T/dt))+1; dt_act = T/(n_steps-1)
    ψ=zeros(ComplexF64,dim); ψ[1]=1.0+0.0im
    k1=similar(ψ); k2=similar(ψ); k3=similar(ψ); k4=similar(ψ); tmp=similar(ψ)
    for step in 0:(n_steps-2)
        t=step*dt_act
        i=clamp(searchsortedlast(knot_t,t),1,nk-1); f=(t-knot_t[i])/(knot_t[i+1]-knot_t[i])
        Ω=Ω_knots[i]+f*(Ω_knots[i+1]-Ω_knots[i]); Δ=Δ_knots[i]+f*(Δ_knots[i+1]-Δ_knots[i])
        h=dt_act; h2=0.5*h; h6=h/6.0
        apply_H!(k1,ψ,Ω,Δ)
        @inbounds for i in 1:dim; tmp[i]=ψ[i]+h2*k1[i]; end; apply_H!(k2,tmp,Ω,Δ)
        @inbounds for i in 1:dim; tmp[i]=ψ[i]+h2*k2[i]; end; apply_H!(k3,tmp,Ω,Δ)
        @inbounds for i in 1:dim; tmp[i]=ψ[i]+h*k3[i]; end; apply_H!(k4,tmp,Ω,Δ)
        @inbounds for i in 1:dim; ψ[i]+=h6*(k1[i]+2k2[i]+2k3[i]+k4[i]); end
    end
    return sum(abs2(ψ[b+1]) for b in mis_bits)
end

# Default linear sweep
Ω_def = [0.0, Ω_MAX, 0.0]
Δ_def = [-Δ_RANGE, -Δ_RANGE, Δ_RANGE]

# Also try moderate sweep
Ω_mod = [0.0, 0.006, 0.006, 0.004, 0.0]
Δ_mod = [-Δ_RANGE, -0.005, 0.0, 0.008, Δ_RANGE]

# Conservative sweep
Ω_cons = [0.0, 0.003, 0.004, 0.003, 0.0]
Δ_cons = [-Δ_RANGE, -0.003, 0.002, 0.005, Δ_RANGE]

@printf("Warm-up... "); flush(stdout)
GC.gc()
p_warm = @time eval_sweep(Ω_def, Δ_def; T=100.0, dt=20.0)
@printf("  P=%.4f\n", p_warm); flush(stdout)

for (name, Ω_k, Δ_k) in [("default linear", Ω_def, Δ_def),
                          ("moderate", Ω_mod, Δ_mod),
                          ("conservative", Ω_cons, Δ_cons)]
    GC.gc()
    @printf("%s sweep... " , name); flush(stdout)
    t0 = time()
    P = eval_sweep(Ω_k, Δ_k; T=2000.0, dt=10.0)
    elapsed = time() - t0
    @printf("P_MIS=%.6f  (%.1fs)\n", P, elapsed); flush(stdout)
end
