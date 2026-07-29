# Quick baseline eval at the challenge's 4000ns parameters
using LinearAlgebra, OrdinaryDiffEq

const C6 = 865.723
const σx = ComplexF64[0 1; 1 0]
const n_op = ComplexF64[0 0; 0 1]
const I2 = ComplexF64[1 0; 0 1]

function embed(op, i, N)
    ops = [I2 for _ in 1:N]; ops[i] = op
    r = ops[1]; for j in 2:N; r = kron(r, ops[j]); end; return r
end

function compute_baseline(positions, label)
    N = size(positions, 2)
    H_Ω = sum(embed(σx, i, N) for i in 1:N) / 2
    H_Δ = -sum(embed(n_op, i, N) for i in 1:N)
    H_int = zeros(ComplexF64, 2^N, 2^N)
    for i in 1:N, j in (i+1):N
        r = sqrt(sum((positions[:,i] - positions[:,j]).^2))
        H_int += (C6 / r^6) * embed(n_op, i, N) * embed(n_op, j, N)
    end

    # 4000ns baseline from challenge spec
    T = 4000.0
    n_pts = 500
    t_rise, t_hold, t_fall = 252.0, 3496.0, 252.0

    function Ω_baseline(t)
        if t < t_rise; return (t/t_rise) * 0.006283
        elseif t < t_rise + t_hold; return 0.006283
        else; return max(0.0, (1 - (t - t_rise - t_hold)/t_fall) * 0.006283)
        end
    end
    function Δ_baseline(t)
        δ0, δf = -0.01257, 0.01257
        if t < t_rise; return δ0
        elseif t < t_rise + t_hold
            f = (t - t_rise) / t_hold
            return δ0 + f * (δf - δ0)
        else; return δf
        end
    end

    function H(t)
        return -im * (H_int + Ω_baseline(t) * H_Ω + Δ_baseline(t) * H_Δ)
    end
    function f!(dψ, ψ, p, t)
        dψ .= H(t) * ψ
    end

    ψ0 = zeros(ComplexF64, 2^N); ψ0[1] = 1.0
    times = collect(range(0.0, T, length=n_pts))
    prob = ODEProblem(f!, ψ0, (0.0, T))
    sol = solve(prob, Tsit5(); saveat=times, abstol=1e-8, reltol=1e-6)
    ψ_final = sol.u[end]

    R_b = (865723.0 / 6.283)^(1/6)
    adj = zeros(Bool, N, N)
    for i in 1:N, j in (i+1):N
        r = sqrt(sum((positions[:,i] - positions[:,j]).^2))
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
        if sz > max_sz; max_sz = sz; mis_bits = [b]
        elseif sz == max_sz; push!(mis_bits, b); end
    end
    P_MIS = sum(abs2(ψ_final[b+1]) for b in mis_bits)
    println("  $label at 4000ns baseline: P_MIS = $P_MIS")
    flush(stdout)
end

ρ = 5.5
star_pos = [0.0   ρ      -ρ/2        -ρ/2; 0.0   0.0     ρ*√3/2     -ρ*√3/2]
s = 5.5
angles = [2π * k / 5 for k in 0:4]
pentagon_pos = [s * cos.(angles)  s * sin.(angles)]'

compute_baseline(star_pos, "Star K₁₃")
compute_baseline(pentagon_pos, "Cycle C₅")
println("Done.")
