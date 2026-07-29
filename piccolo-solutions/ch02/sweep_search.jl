# Sweep parameter search for star K₁₃ — try longer times + better shapes
using LinearAlgebra, OrdinaryDiffEq

const C6 = 865.723
const σx = ComplexF64[0 1; 1 0]; const n_op = ComplexF64[0 0; 0 1]
const I2 = ComplexF64[1 0; 0 1]

function embed(op, i, N)
    ops = [I2 for _ in 1:N]; ops[i] = op
    r = ops[1]; for j in 2:N; r = kron(r, ops[j]); end; return r
end

function eval_P(P, T, n_steps=500)
    N = size(P, 2)
    H_Ω = sum(embed(σx, i, N) for i in 1:N) / 2
    H_Δ = -sum(embed(n_op, i, N) for i in 1:N)
    H_int = zeros(ComplexF64, 2^N, 2^N)
    for i in 1:N, j in (i+1):N
        r = sqrt(sum((P[:,i] - P[:,j]).^2))
        H_int += (C6 / r^6) * embed(n_op, i, N) * embed(n_op, j, N)
    end
    # Cubic profile for Ω (smooth turn-on/off) and Δ (shaped sweep)
    function Ω_fn(t, T, Ω0); x = t/T; return Ω0 * 16 * x^2 * (1-x)^2; end
    # HOLD is fraction of time to spend at delta~0 for population transfer
    function Δ_fn(t, T, Δ0, Δf, hold)
        x = t/T
        if x < hold/2; return Δ0 + (2*x/hold) * (0 - Δ0)
        elseif x < 1-hold/2; return 0.0
        else; return (x - (1-hold/2)) / (hold/2) * Δf
        end
    end
    function H(t, p)
        Ω0, Δ0, Δf, h = p
        return -im * (H_int + Ω_fn(t, T, Ω0) * H_Ω + Δ_fn(t, T, Δ0, Δf, h) * H_Δ)
    end
    ψ0 = zeros(ComplexF64, 2^N); ψ0[1] = 1.0
    times = collect(range(0.0, T, length=n_steps))
    prob = ODEProblem((dψ,ψ,p,t) -> dψ .= H(t, p), ψ0, (0.0, T), [0.006, -0.01257, 0.01257, 0.5])
    sol = solve(prob, Tsit5(); saveat=times, abstol=1e-8, reltol=1e-6)
    ψ_final = sol.u[end]
    R_b = (865723.0 / 6.283)^(1/6)
    adj = zeros(Bool, N, N)
    for i in 1:N, j in (i+1):N
        r = sqrt(sum((P[:,i] - P[:,j]).^2))
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
        if sz > max_sz; max_sz = sz; mis_bits = [b]; elseif sz == max_sz; push!(mis_bits, b); end
    end
    return sum(abs2(ψ_final[b+1]) for b in mis_bits)
end

ρ = 5.5
star_pos = [0.0   ρ      -ρ/2        -ρ/2; 0.0   0.0     ρ*√3/2     -ρ*√3/2]
s = 5.5
angles = [2π * k / 5 for k in 0:4]
pentagon_pos = [s * cos.(angles)  s * sin.(angles)]'

println("═══ Sweep search — Star K₁₃ ═══")
for T in [1000, 1500, 2000, 2500, 3000, 4000]
    P = eval_P(star_pos, Float64(T))
    println("  Star at T=$(T)ns: P_MIS = $(round(P, digits=6))")
end

println("\n═══ Sweep search — Cycle C₅ ═══")
for T in [1000, 1500, 2000, 2500, 3000, 4000]
    P = eval_P(pentagon_pos, Float64(T))
    println("  Pent at T=$(T)ns: P_MIS = $(round(P, digits=6))")
end
println("Done.")
