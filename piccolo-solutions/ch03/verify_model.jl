#!/usr/bin/env julia
# Verify MIS model: dense vs sparse, norm conservation, P_MIS match
using LinearAlgebra, SparseArrays, Printf, Random
Random.seed!(42)

const C6 = 865.723; const Ω_MAX = 0.012566

N = 10; dim = 2^N
@printf("═══ Verification at N=%d (dim=%d) ═══\n", N, dim)
flush(stdout)

# ── Lattice positions ───────────────────────────────────────────────────
R_b = (C6 * 1e3 / 6.283)^(1/6)
a = 0.85 * R_b; nx, ny = 5, 2
positions = zeros(2, N)
for idx in 1:N
    i, j = (idx-1)%nx, (idx-1)÷nx
    jitter = 0.1*a*(2*rand(2).-1)
    positions[:, idx] = [i*a, j*a] + jitter
end

adj = zeros(Bool, N, N)
for i in 1:N, j in (i+1):N
    r = sqrt(sum((positions[:,i] - positions[:,j]).^2))
    adj[i,j] = adj[j,i] = r < R_b
end
@printf("R_b=%.1fµm  edges=%d\n", R_b, sum(adj)÷2); flush(stdout)

# ── MIS (backtracking) ──────────────────────────────────────────────────
function get_mis(adj)
    Ns = size(adj,1); best=Vector{Vector{Int}}(); best_sz=0
    function bt(v, c)
        isempty(c) && (l=length(v); if l>best_sz; best_sz=l; empty!(best); push!(best,copy(v))
        elseif l==best_sz; push!(best,copy(v)); end; return)
        length(v)+length(c)<best_sz && return
        x=c[1]; bt([v;x],[u for u in c if u!=x&&!adj[x,u]]); bt(v,c[2:end])
    end
    bt(Int[],collect(1:Ns))
    [begin b=0; for v in vs; b|=1<<(Ns-v); end; b end for vs in best]
end
mis_bits = get_mis(adj)
@printf("|MIS|=%d  states=%d\n", mis_bits==[] ? 0 : maximum(count_ones(b) for b in mis_bits), length(mis_bits))
flush(stdout)

# ── Dense Hamiltonian ───────────────────────────────────────────────────
bit_masks = [1 << (N-i) for i in 1:N]
H_dense = zeros(ComplexF64, dim, dim)
for b in 0:dim-1
    n = count_ones(b)
    E = 0.0
    for i in 1:N, j in (i+1):N
        r = sqrt(sum((positions[:,i]-positions[:,j]).^2))
        E += (C6/r^6)*((b>>(N-i))&1)*((b>>(N-j))&1)
    end
    H_dense[b+1,b+1] = E
    for mask in bit_masks
        H_dense[b+1, xor(b,mask)+1] += 0.5
    end
end

# ── Sparse H_Ω ──────────────────────────────────────────────────────────
nnz = dim * N
colptr = Vector{Int}(undef, dim+1); for i in 1:dim+1; colptr[i]=(i-1)*N+1; end
rowval = Vector{Int}(undef, nnz); nzval = Vector{Float64}(undef, nnz)
for b in 0:dim-1, (j,mask) in enumerate(bit_masks)
    rowval[b*N+j] = xor(b,mask)+1
    nzval[b*N+j] = 0.5
end
H_Ω = SparseMatrixCSC(dim, dim, colptr, rowval, nzval)

H_Δ_diag = Float64[count_ones(b) for b in 0:dim-1]
V_mat = zeros(N,N)
for i in 1:N, j in (i+1):N
    r = sqrt(sum((positions[:,i]-positions[:,j]).^2))
    V_mat[i,j] = V_mat[j,i] = C6/r^6
end
E_int = zeros(Float64, dim)
for b in 0:dim-1, i in 1:N, j in (i+1):N
    V_mat[i,j]!=0 && (E_int[b+1] += V_mat[i,j]*((b>>(N-i))&1)*((b>>(N-j))&1))
end

# ═══════════════ Test 1: H·ψ (dense vs sparse) ═════════════════════════
@printf("\n─── Test 1: H·ψ match ───\n")
ψ = randn(ComplexF64, dim); ψ ./= norm(ψ)
Ω, Δ = 0.006, -0.012

dψ_dense = zeros(ComplexF64, dim)
mul!(dψ_dense, H_dense, ψ, -im*Ω, zero(ComplexF64))
dψ_dense .+= (-im*(-Δ))*[count_ones(b) for b in 0:dim-1].*ψ  # -im * (-Δ*n) * ψ = i*Δ*n*ψ
# Wait, let me be careful. H = Ω/2*σ^x + (-Δ)*n + E_int
# H_dense = 0.5*σ^x + E_int (has off-diagonal + interaction)
# H_full*ψ = Ω*0.5*σ^x*ψ + (-Δ)n*ψ + E_int*ψ
# = Ω*H_dense_off*ψ + (-Δ)n*ψ + E_int*ψ
# = Ω*(H_dense - diag(E_int))*ψ + (-Δ)n*ψ + E_int*ψ
# = Ω*H_dense*ψ + (1-Ω)*E_int*ψ + (-Δ)*n*ψ
# Hmm, let me just build H_full properly.

# Correct approach:
# H_full = Ω/2*σ^x + (-Δ)*n + E_int
# H_dense = 0.5*σ^x + E_int (the raw matrix)
# H_full*ψ = Ω*(0.5*σ^x*ψ) + (-Δ)*n.*ψ + E_int.*ψ
# 0.5*σ^x*ψ = (H_dense - diag(E_int))*ψ
# So: H_full*ψ = Ω*(H_dense*ψ - E_int.*ψ) + (-Δ)*n.*ψ + E_int.*ψ
# = Ω*H_dense*ψ + (-Ω+1)*E_int.*ψ + (-Δ)*n.*ψ
# Let me just do it elementwise correctly.

# H_full*ψ elementwise:
# (H_full*ψ)[b] = Ω/2 * Σ_j ψ[xor(b, mask_j)] + (-Δ)*count_ones(b)*ψ[b] + E_int[b]*ψ[b]
# = Ω*(0.5*Σ_j ψ[xor(b,mask_j)]) + (-Δ*n + E_int)*ψ[b]

# Using H_dense (which has 0.5*σ^x + E_int):
# (H_dense*ψ)[b] = 0.5*Σ_j ψ[xor(b,mask_j)] + E_int[b]*ψ[b]
# So 0.5*Σ_j ψ[xor(b,mask_j)] = (H_dense*ψ)[b] - E_int[b]*ψ[b]
# Then (H_full*ψ)[b] = Ω*((H_dense*ψ)[b] - E_int[b]*ψ[b]) + (-Δ*n + E_int)*ψ[b]
# = Ω*(H_dense*ψ)[b] + (1-Ω)*E_int[b]*ψ[b] + (-Δ)*n*ψ[b]

# Sparse path:
# dψ_sparse = -i * H_full * ψ
# Diagonal: -i * (-Δ*n + E_int) * ψ
# Off-diagonal: -i * Ω/2 * Σ ψ[xor(b, mask)]

# Let me just test the sparse against direct elementwise:
dψ_expected = zeros(ComplexF64, dim)
for b in 0:dim-1
    s = 0.0+0.0im
    for mask in bit_masks
        s += ψ[xor(b,mask)+1]
    end
    dψ_expected[b+1] = -im*(Ω/2*s + (-Δ*count_ones(b) + E_int[b+1])*ψ[b+1])
end

# Sparse
dψ_sparse = zeros(ComplexF64, dim)
@inbounds @simd for b in 1:dim
    dψ_sparse[b] = -im * (E_int[b] - Δ * H_Δ_diag[b]) * ψ[b]
end
mul!(dψ_sparse, H_Ω, ψ, -im * Ω, one(ComplexF64))

diff = norm(dψ_sparse - dψ_expected) / norm(dψ_expected)
@printf("H·ψ relative diff: %.2e  %s\n", diff, diff < 1e-14 ? "✓" : "✗")
flush(stdout)

# ═══════════════ Test 2: Norm conservation (50 RK4 steps) ═══════════════
@printf("\n─── Test 2: Norm conservation ───\n")

function rk4_step_sparse!(ψ, dt, Ω, Δ)
    dim = length(ψ)
    k1 = similar(ψ); k2 = similar(ψ); k3 = similar(ψ); k4 = similar(ψ); tmp = similar(ψ)
    @inbounds @simd for b in 1:dim; k1[b] = -im*(E_int[b]-Δ*H_Δ_diag[b])*ψ[b]; end
    mul!(k1, H_Ω, ψ, -im*Ω, one(ComplexF64))
    @. tmp = ψ + 0.5*dt*k1
    @inbounds @simd for b in 1:dim; k2[b] = -im*(E_int[b]-Δ*H_Δ_diag[b])*tmp[b]; end
    mul!(k2, H_Ω, tmp, -im*Ω, one(ComplexF64))
    @. tmp = ψ + 0.5*dt*k2
    @inbounds @simd for b in 1:dim; k3[b] = -im*(E_int[b]-Δ*H_Δ_diag[b])*tmp[b]; end
    mul!(k3, H_Ω, tmp, -im*Ω, one(ComplexF64))
    @. tmp = ψ + dt*k3
    @inbounds @simd for b in 1:dim; k4[b] = -im*(E_int[b]-Δ*H_Δ_diag[b])*tmp[b]; end
    mul!(k4, H_Ω, tmp, -im*Ω, one(ComplexF64))
    @. ψ += (dt/6)*(k1 + 2*k2 + 2*k3 + k4)
end

let
    ψ_n = zeros(ComplexF64, dim); ψ_n[1] = 1.0
    drift = 0.0
    for step in 1:100
        t = step*10.0; tf = t/2000.0
        Δ_t = -0.012 + 0.024*tf; Ω_t = 0.006*(1-cospi(tf))/2
        rk4_step_sparse!(ψ_n, 10.0, Ω_t, Δ_t)
        drift = max(drift, abs(norm(ψ_n)-1.0))
    end
    @printf("Max norm drift over 100 steps: %.2e  %s\n", drift,
            drift < 1e-10 ? "✓ Unitary" : "✗ Drifting")
end
flush(stdout)

# ═══════════════ Test 3: Dense vs sparse P_MIS full sweep ═══════════════
@printf("\n─── Test 3: Full sweep P_MIS (dense vs sparse) ───\n")

function sweep_pmis(use_sparse; T=2000.0, dt=10.0)
    n_steps = Int(round(T/dt))+1; dt_a = T/(n_steps-1)
    ψ = zeros(ComplexF64, dim); ψ[1] = 1.0
    if !use_sparse
        H_full = zeros(ComplexF64, dim, dim)
    end
    for step in 0:n_steps-2
        t = step*dt_a; f = t/T
        Ω_t = Ω_MAX*sinpi(f)
        Δ_t = -0.012 + 0.024*f
        if use_sparse
            rk4_step_sparse!(ψ, dt_a, Ω_t, Δ_t)
        else
            # dense
            for b1 in 0:dim-1
                H_full[b1+1,b1+1] = -Δ_t*count_ones(b1) + E_int[b1+1]
                for mask in bit_masks
                    H_full[b1+1,xor(b1,mask)+1] = Ω_t/2
                end
            end
            k1 = zeros(ComplexF64, dim); k2 = zeros(ComplexF64, dim)
            k3 = zeros(ComplexF64, dim); k4 = zeros(ComplexF64, dim); tmp = zeros(ComplexF64, dim)
            mul!(k1, H_full, ψ, -im, zero(ComplexF64))
            @. tmp = ψ + 0.5*dt_a*k1; mul!(k2, H_full, tmp, -im, zero(ComplexF64))
            @. tmp = ψ + 0.5*dt_a*k2; mul!(k3, H_full, tmp, -im, zero(ComplexF64))
            @. tmp = ψ + dt_a*k3; mul!(k4, H_full, tmp, -im, zero(ComplexF64))
            @. ψ += (dt_a/6)*(k1 + 2k2 + 2k3 + k4)
        end
    end
    P = sum(abs2(ψ[b+1]) for b in mis_bits)
    return P, norm(ψ)
end

let
    Pd, nd = sweep_pmis(false)
    Ps, ns = sweep_pmis(true)
    @printf("Dense:  P_MIS=%.10f  norm=%.10f\n", Pd, nd)
    @printf("Sparse: P_MIS=%.10f  norm=%.10f\n", Ps, ns)
    @printf("P_MIS diff: %.2e  %s\n", abs(Pd-Ps), abs(Pd-Ps)<1e-12 ? "✓" : "✗")
end
flush(stdout)

@printf("\n═══ VERDICT ═══\n")
all_ok = diff < 1e-14 && max_drift < 1e-10 && abs(P_d-P_s) < 1e-12
@printf("%s\n", all_ok ? "ALL CHECKS PASS. Model is correct. ✓" : "SOME CHECKS FAILED. See above.")
