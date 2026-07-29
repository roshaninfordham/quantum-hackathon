# Ch02 — MIS via Piccolo optimal control
# Star K₁₃ (4 atoms, unique MIS) and Cycle C₅ (5 atoms, degenerate MIS).
# ZeroOrderPulse + SmoothPulseProblem + L-BFGS (limited-memory Hessian).

using Piccolo
using LinearAlgebra, JLD2, Printf

const C6    = 865_723.0e-3
const O_MAX = 0.012566370614359172
const D_MAX = 0.12566370614359172

σx = ComplexF64[0 1; 1 0]
n  = ComplexF64[0 0; 0 1]
I2 = ComplexF64[1 0; 0 1]

function embed(op, i, N)
    ops = [I2 for _ in 1:N]; ops[i] = op
    return foldl(kron, ops)
end

function build_system(positions)
    N = size(positions, 2)
    H_O  = sum(embed(σx, i, N) for i in 1:N) / 2
    H_D  = sum(embed(n,  i, N) for i in 1:N)
    H_int = zeros(ComplexF64, 2^N, 2^N)
    for i in 1:N, j in (i+1):N
        r = sqrt(sum((positions[:,i] - positions[:,j]).^2))
        H_int += (C6 / r^6) * embed(n, i, N) * embed(n, j, N)
    end
    return H_int, H_O, H_D
end

function find_mis(positions)
    N = size(positions, 2)
    R_b = 7.2
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
    return mis_bits
end

function solve_mis(name, positions; T=800.0, N_steps=60, max_iter=200,
                   du_b=5e-4, ddu_b=5e-5, label="")
    N = size(positions, 2)
    dim = 2^N
    mis_bits = find_mis(positions)

    H_int, H_O, H_D = build_system(positions)
    ψ0 = zeros(ComplexF64, dim); ψ0[1] = 1.0

    N_mis = length(mis_bits)
    if N_mis == 1
        ψ_target = zeros(ComplexF64, dim)
        ψ_target[mis_bits[1] + 1] = 1.0
        @printf("  %s N=%d dim=%d unique MIS bit=0x%02x\n",
                label, N, dim, mis_bits[1])
    else
        ψ_target = zeros(ComplexF64, dim)
        for b in mis_bits
            ψ_target[b + 1] = 1.0 / sqrt(N_mis)
        end
        @printf("  %s N=%d dim=%d %d degenerate MIS states\n",
                label, N, dim, N_mis)
    end
    flush(stdout)

    sys = QuantumSystem(H_int, [H_O, H_D], [(0.0, O_MAX), (-D_MAX, D_MAX)])

    times = collect(range(0.0, T, length=N_steps))
    Ω_init = (O_MAX/3) * abs2.(sin.(π * (times ./ T)))
    Δ_init = range(-D_MAX/10, D_MAX/10, length=N_steps)
    umat = vcat(Ω_init', Δ_init')
    pulse = ZeroOrderPulse(umat, times; initial_value=[0.0, 0.0],
                           final_value=[0.0, 0.0])

    qtraj = KetTrajectory(sys, pulse, ψ0, ψ_target)
    qcp = SmoothPulseProblem(qtraj, N_steps;
        piccolo_options = PiccoloOptions(timesteps_all_equal = true),
        du_bound = du_b, ddu_bound = ddu_b,
        Q = 100.0, R_u = 1e-6, R_du = 1e-5)

    solve!(qcp; max_iter = max_iter, print_level = 1,
           hessian_approximation = "limited-memory",
        callback = Piccolo.Callbacks.callback_factory(
            (opt, st; kwargs...) -> begin
                k = Int(st.iter_count)
                if k % 10 == 0
                    @printf("  iter=%d f=%.6e inf_pr=%.3e inf_du=%.3e\n",
                            k, st.obj_value, st.inf_pr, st.inf_du)
                    flush(stdout)
                end; return true
            end))

    ψ_raw = ket_rollout(get_trajectory(qcp), sys)[:, end]
    ψ_final = ComplexF64[ψ_raw[i] + im * ψ_raw[i + dim] for i in 1:dim]
    P_MIS = sum(abs2(ψ_final[b+1]) for b in mis_bits)
    F_target = abs2(dot(ψ_target, ψ_final))

    @printf("  >>> F_target = %.8f  P_MIS = %.8f\n", F_target, P_MIS)
    flush(stdout)
    return (P_MIS = P_MIS, F_target = F_target, ψ_final = ψ_final,
            mis_bits = mis_bits)
end

println("═══ Ch02 — MIS via Piccolo OC (L-BFGS) ═══")
flush(stdout)

# Star K₁₃
ρ = 5.5
star_pos = [0.0   ρ      -ρ/2        -ρ/2;
            0.0   0.0     ρ*√3/2     -ρ*√3/2]
star = solve_mis("Star K₁₃", star_pos; T=800.0, N_steps=60, max_iter=200,
                 label="star")

# Cycle C₅
s = 5.5
angles = [2π * k / 5 for k in 0:4]
pent_pos = [s * cos.(angles)  s * sin.(angles)]'
pent = solve_mis("Cycle C₅", pent_pos; T=800.0, N_steps=60, max_iter=200,
                 label="pent")

println("\n═══ RESULTS ═══")
@printf("  Star K₁₃:  P_MIS = %.8f (Bezier: 1.00007)\n", star.P_MIS)
@printf("  Cycle C₅:  P_MIS = %.8f (Bezier: 0.999015)\n", pent.P_MIS)
flush(stdout)

JLD2.save("ch02_results.jld2",
          "star_P_MIS", star.P_MIS, "star_ψ", star.ψ_final,
          "pent_P_MIS", pent.P_MIS, "pent_ψ", pent.ψ_final)
println("\nDone.")
flush(stdout)
