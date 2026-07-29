#!/usr/bin/env julia
# Challenge 02 — Optimize sweep parameters for higher P_MIS via Nelder-Mead (sparse engine)
# Runs locally; writes best params + P_MIS to disk every 50 iters.

using LinearAlgebra, OrdinaryDiffEq, SparseArrays, Printf, Random, TOML
Random.seed!(137)

const C6 = 865.723
const Ω_MAX = 0.012566
const Δ_RANGE = 0.01257  # ±12.57 rad/µs

include("../lib/mis_sparse.jl")

# ── Optimizer: Nelder-Mead over [Ω_knots[2:5], Δ_knots[2:5]] (8 params) ──
# Always keep Ω[1]=Ω[end]=0, Δ[1]=Δ[end] fixed at sweep endpoints.
# Free params: Ω[2], Ω[3], Ω[4], Ω[5], Δ[2], Δ[3], Δ[4], Δ[5]
function make_sweep(params)
    a = 0.1; b = 1.0 - a
    Ω_0 = 0.0; Ω_knots = [0.0, params[1], params[2], params[3], params[4], 0.0]
    Δ_0 = -Δ_RANGE; Δ_f = Δ_RANGE
    Δ_knots = [Δ_0, Δ_0 + b*params[5]*(Δ_f-Δ_0), Δ_0 + b*params[6]*(Δ_f-Δ_0),
               Δ_0 + b*params[7]*(Δ_f-Δ_0), Δ_0 + b*params[8]*(Δ_f-Δ_0), Δ_f]
    return Ω_knots, Δ_knots
end

function neg_pmis(params, N, pos, T, n_steps; verbose=false)
    Ω_knots, Δ_knots = make_sweep(params)
    Ω_knots_c = max.(0.0, min.(Ω_MAX, Ω_knots))
    Δ_knots_c = max.(-Δ_RANGE, min.(Δ_RANGE, Δ_knots))
    P = eval_pmis(Ω_knots_c, Δ_knots_c, pos; T=T, n_steps=n_steps)
    verbose && @printf("  P_MIS=%.6f params=[%s]\n", P, join(round.(params, digits=4), " "))
    return -P
end

function nelder_mead(f, x0; max_iter=500, tol=1e-6, α=1.0, γ=2.0, ρ=0.5, σ=0.5)
    n = length(x0)
    # Initial simplex: x0 + perturbations along each axis
    S = [copy(x0) for _ in 1:n+1]
    for i in 1:n
        S[i+1][i] += 0.15 * (abs(x0[i]) > 0 ? abs(x0[i]) : 0.15)
    end
    y = [f(S[i]) for i in 1:n+1]

    best_val = Inf
    for iter in 1:max_iter
        perm = sortperm(y)
        Sp, yp = S[perm], y[perm]
        if yp[1] < best_val
            best_val = yp[1]
            if iter % 50 == 0 || iter == 1
                @printf("  iter=%d best P_MIS=%.6f\n", iter, -best_val)
            end
        end
        if yp[end] - yp[1] < tol * (1 + abs(yp[1])); break; end

        x0 = sum(Sp[1:n]) / n
        xr = x0 + α * (x0 - Sp[end])
        yr = f(xr)

        if yp[1] ≤ yr < yp[end-1]
            Sp[end] = xr; yp[end] = yr
        elseif yr < yp[1]
            xe = x0 + γ * (xr - x0); ye = f(xe)
            if ye < yr; Sp[end] = xe; yp[end] = ye
            else; Sp[end] = xr; yp[end] = yr; end
        else
            if yr < yp[end]
                xc = x0 + ρ * (xr - x0); yc = f(xc)
                if yc < yr
                    Sp[end] = xc; yp[end] = yc
                else; for i in 2:n+1; Sp[i] = Sp[1] + σ * (Sp[i] - Sp[1]); yp[i] = f(Sp[i]); end; end
            else
                xc = x0 - ρ * (x0 - Sp[end]); yc = f(xc)
                if yc < yp[end]
                    Sp[end] = xc; yp[end] = yc
                else; for i in 2:n+1; Sp[i] = Sp[1] + σ * (Sp[i] - Sp[1]); yp[i] = f(Sp[i]); end; end
            end
        end
        S, y = Sp, yp
    end
    perm = sortperm(y)
    return S[perm[1]], -y[perm[1]]
end

# ═══════════════════════════════════════════════════════════════════════
function optimize_graph(name, pos; T=2000.0, n_steps=200, max_iter=400)
    N = size(pos, 2)
    @printf("\n═══ Optimizing %s (N=%d, dim=%d, T=%.0fns) ═══\n", name, N, 2^N, T)
    flush(stdout)

    # Initial params: Ω mid at 0.006, Δ at 30%, 50%, 70%, 85%
    x0 = [0.006, 0.006, 0.006, 0.006, 0.3, 0.5, 0.7, 0.85]
    f(x) = neg_pmis(x, N, pos, T, n_steps)

    # Evaluate initial
    P0 = -f(x0)
    @printf("  Initial P_MIS = %.6f\n", P0)
    flush(stdout)

    x_best, P_best = nelder_mead(f, x0; max_iter=max_iter)
    Ω_k, Δ_k = make_sweep(x_best)
    Ω_k = max.(0.0, min.(Ω_MAX, Ω_k))
    Δ_k = max.(-Δ_RANGE, min.(Δ_RANGE, Δ_k))
    @printf("\n  >>> Best value: P_MIS = %.6f\n", P_best)
    @printf("  >>> Ω knots: %s\n", join(round.(Ω_k, digits=6), " "))
    @printf("  >>> Δ knots: %s\n", join(round.(Δ_k, digits=6), " "))
    flush(stdout)

    open("ch02_opt_$(replace(name, r"\\s+" => "_")).toml", "w") do io
        println(io, "graph = \"$(name)\"")
        println(io, "P_MIS = $(P_best)")
        println(io, "T = $(T)")
        println(io, "Ω_knots = [$(join(round.(Ω_k, digits=6), ", "))]")
        println(io, "Δ_knots = [$(join(round.(Δ_k, digits=6), ", "))]")
    end
    @printf("  Saved to ch02_opt_%s.toml\n", replace(name, r"\\s+" => "_"))

    return (P_MIS=P_best, Ω_knots=Ω_k, Δ_knots=Δ_k)
end

# ── Star K₁₃ ──
ρ = 5.5
star_pos = [0.0   ρ      -ρ/2        -ρ/2; 0.0   0.0     ρ*√3/2     -ρ*√3/2]
star_res = optimize_graph("star_K13", star_pos; T=4000.0, n_steps=300, max_iter=300)

# ── Cycle C₅ ──
s = 5.5
angles = [2π * k / 5 for k in 0:4]
pentagon_pos = [s * cos.(angles)  s * sin.(angles)]'
pent_res = optimize_graph("cycle_C5", pentagon_pos; T=2000.0, n_steps=300, max_iter=300)

println("\n═══ FINAL OPTIMIZED RESULTS ═══")
println("  Star K₁₃  P_MIS = $(star_res.P_MIS)  (was 0.949)")
println("  Cycle C₅  P_MIS = $(pent_res.P_MIS)  (was 0.821)")
flush(stdout)
