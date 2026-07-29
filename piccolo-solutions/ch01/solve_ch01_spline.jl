#!/usr/bin/env julia
# Ch01 re-solve — cubic spline pulse + minimum time
# |Ψ⁺⟩ Bell state on 2 Rydberg atoms at r=5.0µm and r=6.5µm

using Piccolo
using LinearAlgebra
using JLD2
using Printf

const C6    = 865_723.0e-3
const Ω_MAX = 0.012566370614359172
const Δ_MAX = 0.12566370614359172
const Ω_REF = 6.283e-3   # rad/ns (2π×1 MHz)

# ── Operators ──────────────────────────────────────────────────────────
σx = ComplexF64[0 1; 1 0]
n  = ComplexF64[0 0; 0 1]
I2 = ComplexF64[1 0; 0 1]
sx1 = kron(σx, I2); sx2 = kron(I2, σx)
n1  = kron(n, I2);  n2  = kron(I2, n)
H_Ω = (sx1 + sx2) / 2
H_Δ = -(n1 + n2)

ψ0 = ComplexF64[1, 0, 0, 0]
ψ_target = ComplexF64[0, 1/√2, 1/√2, 0]; ψ_target /= norm(ψ_target)
V(r) = C6 / r^6

function build_spline_pulse(T, n_knots)
    knot_times = collect(range(0.0, T, length=n_knots))
    # Initial guess: Ω ~ Ω_REF with gaussian envelope, Δ ~ 0
    Ω_knots = [Ω_REF * exp(-4 * (t/T - 0.5)^2) for t in knot_times]
    Δ_knots = zeros(n_knots)
    u_mat = [Ω_knots'; Δ_knots']  # (2, n_knots)
    # Zero derivative at endpoints for clamped cubic spline
    derivs = zeros(2, n_knots)
    # Leave interior derivatives free (small perturbation)
    pulse = CubicSplinePulse(u_mat, derivs, knot_times;
        initial_value=[0.0, 0.0], final_value=[0.0, 0.0])
    return pulse
end

function solve_fixed_time(r, V, label, tag; T=500.0, n_knots=12, N=100, max_iter=80)
    @printf("\n═══ Fixed-time solve: r=%.1fµm (%s), T=%.0fns ═══\n", r, label, T)
    flush(stdout)

    H_drift = V * kron(n, n)
    sys = QuantumSystem(H_drift, [H_Ω, H_Δ], [(0.0, Ω_MAX), (-Δ_MAX, Δ_MAX)])

    pulse = build_spline_pulse(T, n_knots)
    qtraj = KetTrajectory(sys, pulse, ψ0, ψ_target)
    qcp = SplinePulseProblem(qtraj, N;
        du_bounds = [(0.0, Ω_MAX/50), (0.0, Δ_MAX/50)],
        R_du = 1e-4, R_u = 1e-6, Q = 1000.0)

    solve!(qcp; max_iter = max_iter, print_level = 1,
        callback = Piccolo.Callbacks.callback_factory(
            (opt, st; kwargs...) -> begin
                k = Int(st.iter_count)
                if k % 10 == 0
                    @printf("  iter=%04d  f=%.6e  inf_pr=%.3e  inf_du=%.3e\n",
                            k, st.obj_value, st.inf_pr, st.inf_du)
                    flush(stdout)
                end; return true
            end))

    traj = get_trajectory(qcp)
    ψ_raw = ket_rollout(traj, sys)[:, end]
    d = length(ψ_target)
    ψ_final = ComplexF64[ψ_raw[i] + im * ψ_raw[i + d] for i in 1:d]
    F = abs2(dot(ψ_target, ψ_final))
    @printf("  >>> F = %.8f  (tag=%s)\n", F, tag)
    flush(stdout)

    # Extract pulse data for plotting
    dv = traj.datavec; blk = 16; ns = traj.N
    Ω_opt = [dv[blk*i + 11] for i in 0:ns-1]
    Δ_opt = [dv[blk*i + 12] for i in 0:ns-1]
    times_opt = collect(range(0.0, T, length=ns))

    # Save
    JLD2.save("/tmp/ch01_$(tag)_ft.jld2",
              "F", F, "r", r, "T", T,
              "Ω", Ω_opt, "Δ", Δ_opt, "t", times_opt,
              "qcp", qcp)

    return (F=F, qcp=qcp, sys=sys, Ω=Ω_opt, Δ=Δ_opt, t=times_opt)
end

function solve_min_time(ft_result, r, label, tag;
                        final_fidelity=0.999, Δt_bounds=(1.0, 50.0), max_iter=60)
    @printf("\n═══ Min-time solve: r=%.1fµm (%s) ═══\n", r, label)
    flush(stdout)

    mt_qcp = MinimumTimeProblem(ft_result.qcp;
        final_fidelity = final_fidelity,
        Δt_bounds = Δt_bounds)

    solve!(mt_qcp; max_iter = max_iter, print_level = 1,
        callback = Piccolo.Callbacks.callback_factory(
            (opt, st; kwargs...) -> begin
                k = Int(st.iter_count)
                if k % 10 == 0
                    @printf("  iter=%04d  f=%.6e  inf_pr=%.3e  inf_du=%.3e\n",
                            k, st.obj_value, st.inf_pr, st.inf_du)
                    flush(stdout)
                end; return true
            end))

    traj = get_trajectory(mt_qcp)
    ψ_raw = ket_rollout(traj, ft_result.sys)[:, end]
    d = 4
    ψ_final = ComplexF64[ψ_raw[i] + im * ψ_raw[i + d] for i in 1:d]
    F = abs2(dot(ψ_target, ψ_final))
    T_total = traj.timestep isa Number ? traj.N * traj.timestep : sum(traj.datavec[blk*i + 9] for i in 0:traj.N-1)
    @printf("  >>> F = %.8f  T ≈ %.1f ns  (tag=%s)\n", F, T_total, tag)
    flush(stdout)

    # Extract pulse data
    dv = traj.datavec; blk = 16; ns = traj.N
    Ω_opt = [dv[blk*i + 11] for i in 0:ns-1]
    Δ_opt = [dv[blk*i + 12] for i in 0:ns-1]
    Δt_vals = [dv[blk*i + 9] for i in 0:ns-1]
    times_opt = [sum(Δt_vals[1:i]) for i in 1:ns]

    JLD2.save("/tmp/ch01_$(tag)_mt.jld2",
              "F", F, "r", r, "T", T_total,
              "Ω", Ω_opt, "Δ", Δ_opt, "t", times_opt,
              "Δt", Δt_vals)

    return (F=F, T=T_total, Ω=Ω_opt, Δ=Δ_opt, t=times_opt)
end

# ── Run both spacings ──────────────────────────────────────────────────
global blk = 16  # for T_total calc in min-time

println("═══ Ch01 — Cubic spline + minimum time ═══")
flush(stdout)

r1_ft = solve_fixed_time(5.0, V(5.0), "strong blockade", "r5")
r2_ft = solve_fixed_time(6.5, V(6.5), "weak blockade", "r6")

r1_mt = solve_min_time(r1_ft, 5.0, "strong blockade", "r5")
r2_mt = solve_min_time(r2_ft, 6.5, "weak blockade", "r6")

# ── Summary ────────────────────────────────────────────────────────────
println("\n═══ RESULTS ═══")
@printf("r=5.0µm  fixed-time: F=%.8f  min-time: F=%.8f  T=%.1fns\n", r1_ft.F, r1_mt.F, r1_mt.T)
@printf("r=6.5µm  fixed-time: F=%.8f  min-time: F=%.8f  T=%.1fns\n", r2_ft.F, r2_mt.F, r2_mt.T)

# Print data for the widget
for (tag, r, ft, mt) in [("r5", 5.0, r1_ft, r1_mt), ("r6", 6.5, r2_ft, r2_mt)]
    println("\n=== WIDGET_DATA:$tag ===")
    println("F_ft=$(ft.F)  F_mt=$(mt.F)  T_mt=$(mt.T)")
    println("Ω_ft=$(join(round.(ft.Ω, digits=8), ','))")
    println("Δ_ft=$(join(round.(ft.Δ, digits=8), ','))")
    println("Ω_mt=$(join(round.(mt.Ω, digits=8), ','))")
    println("Δ_mt=$(join(round.(mt.Δ, digits=8), ','))")
    println("t_mt=$(join(round.(mt.t, digits=1), ','))")
end

println("\nDone.")
flush(stdout)
