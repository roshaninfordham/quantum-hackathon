#!/usr/bin/env julia
# Quick timing: matrix-free H·ψ at N=20, one ODE solve
using LinearAlgebra, OrdinaryDiffEq, Printf, Random
Random.seed!(42)

const C6 = 865.723; const Ω_MAX = 0.012566; const Δ_MAX = 0.12566; const Δ_RANGE = 0.01257

N = 20; L = 30.0
positions = L * rand(2, N)
R_b = (C6 * 1e3 / 6.283)^(1 / 6)
@printf("R_b=%.1fµm\n", R_b); flush(stdout)

# diag operators
dim = 2^N
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
    @inbounds @simd for b in 1:dim
        dψ[b] = -im * (E_int[b] - Δ * H_Δ_diag[b]) * ψ[b]
    end
    factor = -im * Ω * 0.5
    @inbounds for mask in bit_masks
        step = 2 * mask
        for base in 0:step:(dim-1)
            for offset in 0:(mask-1)
                b = base + offset + 1
                b2 = base + offset + mask + 1
                v = factor * ψ[b2]; w = factor * ψ[b]
                dψ[b] += v; dψ[b2] += w
            end
        end
    end
end

# Quick timing: time a single apply_H!
ψ = zeros(ComplexF64, dim); ψ[1] = 1.0
dψ = similar(ψ)
@printf("Timing apply_H! (1 call)... ")
flush(stdout)
@time apply_H!(dψ, ψ, 0.006, 0.0)
@printf("  done\n"); flush(stdout)

# Now time a full ODE solve
Ω_k = [0.0, 0.006, 0.006, 0.006, 0.006, 0.006, 0.006, 0.0]
Δ_k = [-Δ_RANGE, -0.008, 0.0, 0.005, 0.005, 0.008, Δ_RANGE, Δ_RANGE]
nk = 8; T = 3000.0
knot_t = collect(range(0.0, T, length=nk))
Ω_f = t -> begin i=clamp(searchsortedlast(knot_t,t),1,nk-1); f=(t-knot_t[i])/(knot_t[i+1]-knot_t[i]); Ω_k[i]+f*(Ω_k[i+1]-Ω_k[i]) end
Δ_f = t -> begin i=clamp(searchsortedlast(knot_t,t),1,nk-1); f=(t-knot_t[i])/(knot_t[i+1]-knot_t[i]); Δ_k[i]+f*(Δ_k[i+1]-Δ_k[i]) end

ψ0 = zeros(ComplexF64, dim); ψ0[1] = 1.0
function ode_f!(dψ, ψ, p, t)
    apply_H!(dψ, ψ, Ω_f(t), Δ_f(t))
end
prob = ODEProblem(ode_f!, ψ0, (0.0, T))

GC.gc()
@printf("Starting ODE solve (T=%.0fns, dim=%d)...\n", T, dim)
flush(stdout)
@time sol = solve(prob, Tsit5(); saveat=[T], abstol=1e-5, reltol=1e-3)
ψ_f = sol.u[end]
E = sum(abs2.(ψ_f))
@printf("Norm=%.6f  Time per eval: see above\n", E)
flush(stdout)
