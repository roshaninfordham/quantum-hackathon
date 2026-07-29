# Ch01 re-solve — ZeroOrderPulse + SmoothPulseProblem
# Hard: du_bound=5e-4 (slew rate), ddu_bound=5e-5 (acceleration)
# Plus soft regularizers for interior gradient.
# Plots use ZOH stairs (piecewise constant).

using Piccolo
using CairoMakie
using LinearAlgebra
using JLD2
using Printf

const C6    = 865_723.0e-3
const O_MAX = 0.012566370614359172
const D_MAX = 0.12566370614359172
const DU_B  = 5e-4         # hard |du/dt| bound (rad/ns²)
const DDU_B = 5e-5         # hard |d²u/dt²| bound (rad/ns³)

sx = ComplexF64[0 1; 1 0]; n = ComplexF64[0 0; 0 1]; I2 = ComplexF64[1 0; 0 1]
sx1 = kron(sx, I2); sx2 = kron(I2, sx)
n1  = kron(n, I2);  n2  = kron(I2, n)
H_O = (sx1 + sx2) / 2; H_D = -(n1 + n2)

p0 = ComplexF64[1, 0, 0, 0]
pt = ComplexF64[0, 1/sqrt(2), 1/sqrt(2), 0]; pt /= norm(pt)
V(r) = C6 / r^6

const N_STP = 100
const T_FIX = 500.0

function zoh_plot(Ω_ft, Δ_ft, Ω_mt, Δ_mt, t_ft, t_mt, pops_ft, pops_mt, r, tag)
    fig = Figure(size=(900, 600), fontsize=11)

    # ── Row 1: fixed-time pulse (ZOH stairs) ──
    ax1 = Axis(fig[1, 1]; xlabel="t (ns)", ylabel="Ω, Δ (rad/ns)",
               title="Fixed-time (T=500ns, F=$(round(pops_ft[1], digits=8)))")
    # ZOH: stairs with step=:post — each value holds until the next sample
    stairs!(ax1, t_ft, Ω_ft; step=:post, color=:dodgerblue, linewidth=1.5, label="Ω")
    stairs!(ax1, t_ft, Δ_ft; step=:post, color=:orange, linewidth=1.5, label="Δ")
    hlines!(ax1, [0]; color=:gray, linestyle=:dash, linewidth=0.5)
    axislegend(ax1; position=:rt)

    # ── Row 2: min-time pulse (ZOH stairs) ──
    ax2 = Axis(fig[2, 1]; xlabel="t (ns)", ylabel="Ω, Δ (rad/ns)",
               title="Min-time (T=$(round(t_mt[end], digits=1))ns, F=$(round(pops_mt[1], digits=8)))")
    stairs!(ax2, t_mt, Ω_mt; step=:post, color=:dodgerblue, linewidth=1.5, label="Ω")
    stairs!(ax2, t_mt, Δ_mt; step=:post, color=:orange, linewidth=1.5, label="Δ")
    hlines!(ax2, [0]; color=:gray, linestyle=:dash, linewidth=0.5)
    axislegend(ax2; position=:rt)

    # ── Row 3: populations ──
    labels = ["|gg⟩" "|gr⟩+|rg⟩" "|rr⟩"]
    colors = [:gray, :dodgerblue, :tomato]
    ax3 = Axis(fig[1:2, 2]; xlabel="t (ns)", ylabel="Population",
               title="Population dynamics (r=$(r)µm)")

    # Interpolate fixed-time pops to common time grid for smooth curves
    for (i, lab, col) in zip(1:3, labels, colors)
        lines!(ax3, t_ft, pops_ft[i+1]; color=col, linewidth=1.5,
               label="FT $lab")
        lines!(ax3, t_mt, pops_mt[i+1]; color=col, linewidth=1.5,
               linestyle=:dash, label="MT $lab")
    end
    axislegend(ax3; position=:rt, nbanks=2, fontsize=9)

    Label(fig[0, :], "Ch01 — r=$(r)µm, du_bound=$(DU_B), ddu_bound=$(DDU_B)",
          fontsize=14, font=:bold)

    save("/tmp/ch01_$(tag)_bounded.png", fig; px_per_unit=2)
    @printf("  saved /tmp/ch01_%s_bounded.png\n", tag)
    flush(stdout)
end

function solve_one(r, Vval, label, tag)
    @printf("\n=== r=%.1fum (%s) ===\n", r, label); flush(stdout)

    # ── Fixed-time ──
    H_d = Vval * kron(n, n)
    sys = QuantumSystem(H_d, [H_O, H_D], [(0.0, O_MAX), (-D_MAX, D_MAX)])

    ts = collect(range(0.0, T_FIX, length=N_STP))
    O_init = [0.006 * exp(-4*(t/T_FIX - 0.5)^2) for t in ts]
    umat = zeros(2, N_STP); umat[1,:] = O_init
    pulse = ZeroOrderPulse(umat, ts; initial_value=[0.0, 0.0], final_value=[0.0, 0.0])
    qtraj = KetTrajectory(sys, pulse, p0, pt)
    qcp = SmoothPulseProblem(qtraj, N_STP;
        piccolo_options = PiccoloOptions(timesteps_all_equal = true),
        du_bound = DU_B, ddu_bound = DDU_B,
        Q = 1000.0, R_u = 1e-7, R_du = 1e-5)

    solve!(qcp; max_iter = 60, print_level = 1,
        callback = Piccolo.Callbacks.callback_factory(
            (opt, st; kwargs...) -> begin
                if Int(st.iter_count) % 10 == 0
                    @printf("  iter=%04d  f=%.6e  inf_pr=%.3e  inf_du=%.3e\n",
                            Int(st.iter_count), st.obj_value, st.inf_pr, st.inf_du)
                    flush(stdout)
                end; return true
            end))

    traj = get_trajectory(qcp)
    dv = traj.datavec; blk = 16
    O_ft = [dv[blk*i + 11] for i in 0:N_STP-1]
    D_ft = [dv[blk*i + 12] for i in 0:N_STP-1]
    pr = ket_rollout(traj, sys)
    pf = ComplexF64[pr[i,end] + im*pr[i+4,end] for i in 1:4]
    F_ft = abs2(dot(pt, pf))
    @printf("  >>> Fixed-time F = %.8f\n", F_ft); flush(stdout)

    # Population dynamics
    N_t = size(pr, 2)
    gg_ft = [pr[1,k]^2 + pr[5,k]^2 for k in 1:N_t]
    be_ft = [(pr[2,k]+pr[3,k])^2 + (pr[6,k]+pr[7,k])^2 for k in 1:N_t]
    rr_ft = [pr[4,k]^2 + pr[8,k]^2 for k in 1:N_t]

    # ── Min-time ──
    mt_qcp = MinimumTimeProblem(qcp; final_fidelity=0.999,
                                Δt_bounds=(0.5, 20.0))

    solve!(mt_qcp; max_iter = 60, print_level = 1,
        callback = Piccolo.Callbacks.callback_factory(
            (opt, st; kwargs...) -> begin
                if Int(st.iter_count) % 10 == 0
                    @printf("  iter=%04d  f=%.6e  inf_pr=%.3e  inf_du=%.3e\n",
                            Int(st.iter_count), st.obj_value, st.inf_pr, st.inf_du)
                    flush(stdout)
                end; return true
            end))

    traj = get_trajectory(mt_qcp)
    dv = traj.datavec; blk = 16; ns = traj.N
    O_mt = [dv[blk*i + 11] for i in 0:ns-1]
    D_mt = [dv[blk*i + 12] for i in 0:ns-1]
    Dt_v = [dv[blk*i + 9] for i in 0:ns-1]
    T_mt = sum(Dt_v)
    t_mt = [sum(Dt_v[1:i]) for i in 1:ns]

    pr = ket_rollout(traj, sys)
    pf = ComplexF64[pr[i,end] + im*pr[i+4,end] for i in 1:4]
    F_mt = abs2(dot(pt, pf))
    @printf("  >>> Min-time F = %.8f  T = %.1f ns\n", F_mt, T_mt); flush(stdout)

    N_t = size(pr, 2)
    gg_mt = [pr[1,k]^2 + pr[5,k]^2 for k in 1:N_t]
    be_mt = [(pr[2,k]+pr[3,k])^2 + (pr[6,k]+pr[7,k])^2 for k in 1:N_t]
    rr_mt = [pr[4,k]^2 + pr[8,k]^2 for k in 1:N_t]

    # ── Save ──
    JLD2.save("/tmp/ch01_$(tag)_bounded.jld2",
              "F_ft", F_ft, "F_mt", F_mt, "r", r,
              "T_ft", T_FIX, "T_mt", T_mt,
              "O_ft", O_ft, "D_ft", D_ft,
              "O_mt", O_mt, "D_mt", D_mt,
              "t_ft", collect(ts), "t_mt", t_mt)

    # ── Plot ──
    pops_ft = (F_ft, gg_ft, be_ft, rr_ft)
    pops_mt = (F_mt, gg_mt, be_mt, rr_mt)
    zoh_plot(O_ft, D_ft, O_mt, D_mt, collect(ts), t_mt,
             pops_ft, pops_mt, r, tag)
end

println("=== Ch01 — bounded du/dt + d²u/dt² ===")
@printf("  du_bound = %.0e rad/ns²\n", DU_B)
@printf("  ddu_bound = %.0e rad/ns³\n", DDU_B)
flush(stdout)

solve_one(5.0, V(5.0), "strong blockade", "r5")
solve_one(6.5, V(6.5), "weak blockade", "r6")

println("\nDone.")
flush(stdout)
