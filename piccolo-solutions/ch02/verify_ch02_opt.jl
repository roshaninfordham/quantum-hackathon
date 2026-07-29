# Verify optimized Ch02 parameters at high precision (dense solver, tight tolerances)
using LinearAlgebra, OrdinaryDiffEq, Printf

const C6 = 865.723
const σx = ComplexF64[0 1; 1 0]; const n_op = ComplexF64[0 0; 0 1]; const I2 = ComplexF64[1 0; 0 1]
embed(op, i, N) = foldl(kron, [j == i ? op : I2 for j in 1:N])

function eval_dense(Ω_knots, Δ_knots, positions; T, n_steps=400, abstol=1e-10, reltol=1e-8)
    N = size(positions, 2); dim = 2^N
    H_Ω = sum(embed(σx, i, N) for i in 1:N) / 2
    H_Δ = -sum(embed(n_op, i, N) for i in 1:N)
    H_int = zeros(ComplexF64, dim, dim)
    for i in 1:N, j in (i+1):N
        r = sqrt(sum((positions[:,i]-positions[:,j]).^2))
        H_int += (C6/r^6) * embed(n_op,i,N) * embed(n_op,j,N)
    end
    n_knots = length(Ω_knots)
    knot_t = collect(range(0.0, T, length=n_knots))
    function f!(dψ, ψ, p, t)
        i = clamp(searchsortedlast(knot_t, t), 1, n_knots-1)
        f = (t - knot_t[i]) / (knot_t[i+1] - knot_t[i])
        Ω = Ω_knots[i] + f*(Ω_knots[i+1]-Ω_knots[i])
        Δ = Δ_knots[i] + f*(Δ_knots[i+1]-Δ_knots[i])
        dψ .= -im * (H_int + Ω*H_Ω + Δ*H_Δ) * ψ
    end
    ψ0 = zeros(ComplexF64, dim); ψ0[1] = 1.0
    times = collect(range(0.0, T, length=n_steps))
    sol = solve(ODEProblem(f!, ψ0, (0.0,T)), Tsit5(); saveat=times, abstol=abstol, reltol=reltol)
    ψf = sol.u[end]
    # Normalization check
    norm_ψ = norm(ψf)
    R_b = (C6*1e3/6.283)^(1/6)
    adj = zeros(Bool,N,N)
    for i in 1:N, j in (i+1):N; r=sqrt(sum((positions[:,i]-positions[:,j]).^2)); adj[i,j]=adj[j,i]=r<R_b; end
    max_sz=0; mis_bits=Int[]
    for b in 0:dim-1
        bits=[(b>>(N-1-k))&1 for k in 0:N-1]; ok=true
        for i in 1:N, j in (i+1):N; if bits[i]==1&&bits[j]==1&&adj[i,j]; ok=false;break;end;end
        if !ok; continue; end; sz=sum(bits)
        if sz>max_sz; max_sz=sz; mis_bits=[b]; elseif sz==max_sz; push!(mis_bits,b); end
    end
    P = sum(abs2(ψf[b+1]) for b in mis_bits)
    return P, norm_ψ
end

# Star K₁₃ — optimized params
ρ = 5.5; star_pos = [0.0 ρ -ρ/2 -ρ/2; 0.0 0.0 ρ*√3/2 -ρ*√3/2]
Ω_star = [0.0, 0.002827, 0.00682, 0.007721, 0.00705, 0.0]
Δ_star = [-0.01257, -0.00825, -0.000465, 0.006477, 0.008555, 0.01257]

println("═══ Ch02 Optimized — High-Precision Verification ═══\n")

P_star, n_star = eval_dense(Ω_star, Δ_star, star_pos; T=4000.0, n_steps=600)
@printf("Star K₁₃:  P_MIS = %.10f  ‖ψ‖ = %.10f  (baseline 0.909)\n", P_star, n_star)

# Pentagon C₅ — optimized params
s = 5.5; angles = [2π * k / 5 for k in 0:4]; pent_pos = [s*cos.(angles) s*sin.(angles)]'
Ω_pent = [0.0, 0.011489, 0.008822, 0.004311, 0.001233, 0.0]
Δ_pent = [-0.01257, -0.004121, -0.001474, 0.004036, 0.002981, 0.01257]

P_pent, n_pent = eval_dense(Ω_pent, Δ_pent, pent_pos; T=2000.0, n_steps=600)
@printf("Cycle C₅:  P_MIS = %.10f  ‖ψ‖ = %.10f  (baseline 0.320)\n", P_pent, n_pent)

println("\n─── Comparison ───")
println("Star  before: 0.949  after: $(round(P_star,digits=6))  baseline: 0.909")
println("Pent  before: 0.821  after: $(round(P_pent,digits=6))  baseline: 0.320")
