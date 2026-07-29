#!/usr/bin/env julia
# Ch03 — MIS at N=15 with grid lattice + Nelder-Mead
using LinearAlgebra, SparseArrays, Printf, Random
Random.seed!(42)

const C6 = 865.723; const Ω_MAX = 0.012566; const Δ_MAX = 0.12566

function run()
    println("═══ Challenge 03 — MIS at N=15 ═══")
    flush(stdout)

    # ── Grid lattice (5×3, avoid close atoms) ──────────────────────────
    N = 15
    dim = 2^N
    R_b = (C6 * 1e3 / 6.283)^(1/6)
    a = 0.85 * R_b
    nx, ny = 5, 3
    positions = zeros(2, N)
    for idx in 1:N
        i = (idx - 1) % nx
        j = (idx - 1) ÷ nx
        jitter = 0.05 * a * (2 * rand(2) .- 1)
        positions[:, idx] = [i * a, j * a] .+ jitter
    end

    adj = zeros(Bool, N, N)
    for i in 1:N, j in (i+1):N
        r = sqrt(sum((positions[:, i] - positions[:, j]) .^ 2))
        adj[i, j] = adj[j, i] = r < R_b
    end
    @printf("N=%d  R_b=%.1fµm  dim=%d  edges=%d\n", N, R_b, dim, sum(adj)÷2)
    flush(stdout)

    # ── MIS enumeration ────────────────────────────────────────────────
    function get_max_mis(adj)
        Ns = size(adj, 1)
        best = Vector{Vector{Int}}()
        bsz = 0
        function bt(v, c)
            if isempty(c)
                l = length(v)
                if l > bsz; bsz = l; empty!(best); push!(best, copy(v))
                elseif l == bsz; push!(best, copy(v)); end
                return
            end
            length(v) + length(c) < bsz && return
            x = c[1]
            bt([v; x], [u for u in c if u != x && !adj[x, u]])
            bt(v, c[2:end])
        end
        bt(Int[], collect(1:Ns))
        [begin b = 0; for v in vs; b |= 1 << (Ns - v); end; b end for vs in best]
    end
    @time mis_bits = get_max_mis(adj)
    mis_sz = mis_bits == [] ? 0 : maximum(count_ones(b) for b in mis_bits)
    @printf("|MIS|=%d  states=%d\n", mis_sz, length(mis_bits))
    flush(stdout)

    # ── Operators ──────────────────────────────────────────────────────
    @printf("Building operators... ")
    flush(stdout)
    @time begin
        bit_masks = [1 << (N - i) for i in 1:N]
        H_Δ_diag = Float64[count_ones(b) for b in 0:(dim - 1)]
        V_mat = zeros(N, N)
        for i in 1:N, j in (i+1):N
            r = sqrt(sum((positions[:, i] - positions[:, j]) .^ 2))
            V_mat[i, j] = V_mat[j, i] = C6 / r^6
        end
        E_int = zeros(Float64, dim)
        for b in 0:(dim - 1), i in 1:N, j in (i+1):N
            V_mat[i, j] != 0 && (E_int[b + 1] += V_mat[i, j] * ((b >> (N - i)) & 1) * ((b >> (N - j)) & 1))
        end
        nnz = dim * N
        colptr = Vector{Int}(undef, dim + 1)
        for i in 1:(dim + 1); colptr[i] = (i - 1) * N + 1; end
        rowval = Vector{Int}(undef, nnz)
        nzval = Vector{Float64}(undef, nnz)
        for b in 0:(dim - 1), (j, mask) in enumerate(bit_masks)
            rowval[b * N + j] = xor(b, mask) + 1
            nzval[b * N + j] = 0.5
        end
        H_Ω = SparseMatrixCSC(dim, dim, colptr, rowval, nzval)
    end
    flush(stdout)

    # ── H·ψ ─────────────────────────────────────────────────────────────
    function apply_H!(dψ, ψ, Ω, Δ)
        @inbounds @simd for b in 1:dim
            dψ[b] = -im * (E_int[b] - Δ * H_Δ_diag[b]) * ψ[b]
        end
        mul!(dψ, H_Ω, ψ, -im * Ω, one(ComplexF64))
    end

    # ── Evaluate sweep ──────────────────────────────────────────────────
    function eval_sweep(Ω_k, Δ_k; T=2000.0, dt=10.0)
        nk = length(Ω_k)
        knot_t = collect(range(0.0, T, length=nk))
        nsteps = Int(round(T / dt)) + 1
        dt_a = T / (nsteps - 1)

        ψ = zeros(ComplexF64, dim); ψ[1] = 1.0 + 0.0im
        k1 = similar(ψ); k2 = similar(ψ); k3 = similar(ψ); k4 = similar(ψ)
        tmp = similar(ψ)

        for step in 0:(nsteps - 2)
            t = step * dt_a
            ix = clamp(searchsortedlast(knot_t, t), 1, nk - 1)
            f = (t - knot_t[ix]) / (knot_t[ix + 1] - knot_t[ix])
            Ω = Ω_k[ix] + f * (Ω_k[ix + 1] - Ω_k[ix])
            Δ = Δ_k[ix] + f * (Δ_k[ix + 1] - Δ_k[ix])

            h = dt_a; h2 = 0.5h; h6 = h / 6.0
            apply_H!(k1, ψ, Ω, Δ)
            @inbounds @simd for i in 1:dim; tmp[i] = ψ[i] + h2 * k1[i]; end
            apply_H!(k2, tmp, Ω, Δ)
            @inbounds @simd for i in 1:dim; tmp[i] = ψ[i] + h2 * k2[i]; end
            apply_H!(k3, tmp, Ω, Δ)
            @inbounds @simd for i in 1:dim; tmp[i] = ψ[i] + h * k3[i]; end
            apply_H!(k4, tmp, Ω, Δ)
            @inbounds @simd for i in 1:dim
                ψ[i] += h6 * (k1[i] + 2k2[i] + 2k3[i] + k4[i])
            end
        end

        P = 0.0
        @inbounds for b in mis_bits; P += abs2(ψ[b + 1]); end
        return P
    end

    # ── Sweep parameterization ──────────────────────────────────────────
    function make_sweep(params)
        n_inner = length(params) ÷ 2
        Ω_knots = [0.0; [max(0.0, min(Ω_MAX, params[i])) for i in 1:n_inner]; 0.0]
        Δ_min = -Ω_MAX * 0.8
        Δ_max = Ω_MAX * 0.5
        Δ_knots = [Δ_min; [Δ_min + (Δ_max - Δ_min) * params[n_inner + i] for i in 1:n_inner]; Δ_max]
        return Ω_knots, Δ_knots
    end

    # ── Nelder-Mead ────────────────────────────────────────────────────
    n_par = 6
    x0 = [0.006, 0.006, 0.006, 0.25, 0.5, 0.75]

    GC.gc()
    @printf("Initial eval... "); flush(stdout)
    t0 = time()
    P0 = eval_sweep(make_sweep(x0)...)
    @printf("P_MIS=%.6f  (%.1fs)\n", P0, time() - t0)
    flush(stdout)

    α, γ, ρ, σ = 1.0, 2.0, 0.5, 0.5
    S = [copy(x0) for _ in 1:n_par+1]
    for i in 1:n_par; S[i+1][i] += 0.2 * (abs(x0[i]) > 0.01 ? abs(x0[i]) : 0.2); end
    GC.gc()
    y = [-eval_sweep(make_sweep(S[i])...) for i in 1:n_par+1]

    best_val = -Inf
    max_iter = 120
    log = open("ch03_n15.log", "w")
    println(log, "Ch03 N=15 Nelder-Mead")
    flush(log)

    for iter in 1:max_iter
        perm = sortperm(y)
        Sp = S[perm]; yp = y[perm]

        if -yp[1] > best_val + 1e-15
            best_val = -yp[1]
            best_x = copy(Sp[1])
            @printf("  iter=%d best P_MIS=%.8f\n", iter, best_val)
            @printf(log, "iter=%d P_MIS=%.8f\n", iter, best_val)
            flush(log); flush(stdout)
        end

        if yp[end] - yp[1] < 1e-8 * (1 + abs(yp[1]))
            @printf("  Converged at iter=%d (range=%.2e)\n", iter, yp[end] - yp[1])
            break
        end

        xbar = sum(Sp[1:n_par]) / n_par
        xr = xbar + α * (xbar - Sp[end])
        yr = -eval_sweep(make_sweep(xr)...)

        if yp[1] ≤ yr < yp[end - 1]
            Sp[end] = xr; yp[end] = yr
        elseif yr < yp[1]
            xe = xbar + γ * (xr - xbar); ye = -eval_sweep(make_sweep(xe)...)
            if ye < yr; Sp[end] = xe; yp[end] = ye else; Sp[end] = xr; yp[end] = yr; end
        else
            if yr < yp[end]
                xc = xbar + ρ * (xr - xbar); yc = -eval_sweep(make_sweep(xc)...)
                if yc < yr; Sp[end] = xc; yp[end] = yc
                else
                    for i in 2:n_par+1
                        Sp[i] = Sp[1] + σ * (Sp[i] - Sp[1])
                        yp[i] = -eval_sweep(make_sweep(Sp[i])...)
                    end
                end
            else
                xc = xbar - ρ * (xbar - Sp[end]); yc = -eval_sweep(make_sweep(xc)...)
                if yc < yp[end]; Sp[end] = xc; yp[end] = yc
                else
                    for i in 2:n_par+1
                        Sp[i] = Sp[1] + σ * (Sp[i] - Sp[1])
                        yp[i] = -eval_sweep(make_sweep(Sp[i])...)
                    end
                end
            end
        end
        S = Sp; y = yp
    end

    perm = sortperm(y)
    x_best = S[perm[1]]
    Ω_k, Δ_k = make_sweep(x_best)
    P_best = -y[perm[1]]

    println("\n════════════════════════════════════")
    @printf("★★★ Ch03 RESULT at N=%d ★★★\n", N)
    @printf("P_MIS = %.8f\n", P_best)
    @printf("Ω knots = %s\n", join(round.(Ω_k, digits=6), "  "))
    @printf("Δ knots = %s\n", join(round.(Δ_k, digits=6), "  "))
    println("════════════════════════════════════")
    @printf(log, "\nFINAL P_MIS=%.8f\n", P_best)
    close(log)

    println("Done. log in ch03_n15.log")
end

run()
