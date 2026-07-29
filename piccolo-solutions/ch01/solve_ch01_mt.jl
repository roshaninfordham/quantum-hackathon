#!/usr/bin/env julia
# Ch01 re-solve — ZeroOrderPulse + SmoothPulseProblem + MinimumTimeProblem
# |+> Bell state on 2 Rydberg atoms at r=5.0um and r=6.5um
# Zero-order hold with derivative regularization (smooth, clamped endpoints)

using Piccolo
using LinearAlgebra
using JLD2
using Printf

const C6    = 865_723.0e-3
const O_MAX = 0.012566370614359172
const D_MAX = 0.12566370614359172

sx = ComplexF64[0 1; 1 0]; n = ComplexF64[0 0; 0 1]; I2 = ComplexF64[1 0; 0 1]
sx1 = kron(sx, I2); sx2 = kron(I2, sx)
n1  = kron(n, I2);  n2  = kron(I2, n)
H_O = (sx1 + sx2) / 2; H_D = -(n1 + n2)

p0 = ComplexF64[1, 0, 0, 0]
pt = ComplexF64[0, 1/sqrt(2), 1/sqrt(2), 0]; pt /= norm(pt)
V(r) = C6 / r^6

const N_STP = 100
const T_FIX = 500.0

function solve_fixed(r, Vval, label, tag)
    @printf("\n=== Fixed-time: r=%.1fum (%s) ===\n", r, label); flush(stdout)

    H_d = Vval * kron(n, n)
    sys = QuantumSystem(H_d, [H_O, H_D], [(0.0, O_MAX), (-D_MAX, D_MAX)])

    ts = collect(range(0.0, T_FIX, length=N_STP))
    O_init = [0.006 * exp(-4*(t/T_FIX - 0.5)^2) for t in ts]
    umat = zeros(2, N_STP); umat[1,:] = O_init
    pulse = ZeroOrderPulse(umat, ts; initial_value=[0.0, 0.0], final_value=[0.0, 0.0])
    qtraj = KetTrajectory(sys, pulse, p0, pt)
    qcp = SmoothPulseProblem(qtraj, N_STP;
        piccolo_options = PiccoloOptions(timesteps_all_equal = true),
        Q = 1000.0, R_u = 1e-6, R_du = 1e-4)

    t0 = time()
    solve!(qcp; max_iter = 40, print_level = 1,
        callback = Piccolo.Callbacks.callback_factory(
            (opt, st; kwargs...) -> begin
                if Int(st.iter_count) % 10 == 0
                    @printf("  iter=%04d  f=%.6e  inf_pr=%.3e  inf_du=%.3e\n",
                            Int(st.iter_count), st.obj_value, st.inf_pr, st.inf_du)
                    flush(stdout)
                end; return true
            end))
    t1 = time()
    @printf("  time: %.1f s\n", t1-t0); flush(stdout)

    traj = get_trajectory(qcp)
    dv = traj.datavec; blk = 16
    O_opt = [dv[blk*i + 11] for i in 0:N_STP-1]
    D_opt = [dv[blk*i + 12] for i in 0:N_STP-1]
    pr = ket_rollout(traj, sys)[:, end]
    pf = ComplexF64[pr[i] + im*pr[i+4] for i in 1:4]
    F = abs2(dot(pt, pf))
    @printf("  >>> F = %.8f  [tag=%s]\n", F, tag); flush(stdout)

    JLD2.save("/tmp/ch01_$(tag)_ft.jld2",
              "F", F, "r", r, "T", T_FIX,
              "O", O_opt, "D", D_opt, "t", collect(ts),
              "qcp", qcp, "sys", sys)

    return (F=F, qcp=qcp, sys=sys, O=O_opt, D=D_opt, t=ts)
end

function solve_min(ft, r, label, tag; f_fid=0.999)
    @printf("\n=== Min-time: r=%.1fum (%s) ===\n", r, label); flush(stdout)

    mt_qcp = MinimumTimeProblem(ft.qcp; final_fidelity=f_fid,
                                Δt_bounds=(0.5, 20.0))

    t0 = time()
    solve!(mt_qcp; max_iter = 50, print_level = 1,
        callback = Piccolo.Callbacks.callback_factory(
            (opt, st; kwargs...) -> begin
                if Int(st.iter_count) % 10 == 0
                    @printf("  iter=%04d  f=%.6e  inf_pr=%.3e  inf_du=%.3e\n",
                            Int(st.iter_count), st.obj_value, st.inf_pr, st.inf_du)
                    flush(stdout)
                end; return true
            end))
    t1 = time()
    @printf("  time: %.1f s\n", t1-t0); flush(stdout)

    traj = get_trajectory(mt_qcp)
    dv = traj.datavec; blk = 16; ns = traj.N
    O_opt = [dv[blk*i + 11] for i in 0:ns-1]
    D_opt = [dv[blk*i + 12] for i in 0:ns-1]
    Dt_v = [dv[blk*i + 9] for i in 0:ns-1]
    T = sum(Dt_v)
    t_v = [sum(Dt_v[1:i]) for i in 1:ns]

    pr = ket_rollout(traj, ft.sys)[:, end]
    pf = ComplexF64[pr[i] + im*pr[i+4] for i in 1:4]
    F = abs2(dot(pt, pf))
    @printf("  >>> F = %.8f  T = %.1f ns  [tag=%s]\n", F, T, tag); flush(stdout)

    JLD2.save("/tmp/ch01_$(tag)_mt.jld2",
              "F", F, "r", r, "T", T,
              "O", O_opt, "D", D_opt, "t", t_v, "Dt", Dt_v)

    return (F=F, T=T, O=O_opt, D=D_opt, t=t_v)
end

println("=== Ch01 — Zero-order + smooth regularizer + minimum time ===")
flush(stdout)

r5f = solve_fixed(5.0, V(5.0), "strong blockade", "r5")
r6f = solve_fixed(6.5, V(6.5), "weak blockade", "r6")

r5m = solve_min(r5f, 5.0, "strong blockade", "r5")
r6m = solve_min(r6f, 6.5, "weak blockade", "r6")

println("\n=== RESULTS ===")
@printf("r=5.0um  fixed: F=%.8f  min-time: F=%.8f  T=%.1fns\n", r5f.F, r5m.F, r5m.T)
@printf("r=6.5um  fixed: F=%.8f  min-time: F=%.8f  T=%.1fns\n", r6f.F, r6m.F, r6m.T)
flush(stdout)

# Print widget data
for (tag, ft, mt) in [("r5", r5f, r5m), ("r6", r6f, r6m)]
    println("\n=== WIDGET_DATA:$tag ===")
    println("F_ft=$(ft.F)  F_mt=$(mt.F)  T_mt=$(mt.T)")
    println("O_ft=$(join(round.(ft.O, digits=8), ','))")
    println("D_ft=$(join(round.(ft.D, digits=8), ','))")
    println("O_mt=$(join(round.(mt.O, digits=8), ','))")
    println("D_mt=$(join(round.(mt.D, digits=8), ','))")
    println("t_mt=$(join(round.(mt.t, digits=1), ','))")
end

println("\nDone.")
flush(stdout)
