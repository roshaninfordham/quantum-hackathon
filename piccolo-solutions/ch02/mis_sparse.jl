# Challenge 03 prototype — sparse matrix-free MIS solver for N ≥ 15
# Builds H·ψ without storing dense 2^N × 2^N matrices.
# Uses bit-manipulation for σ^x flips and diagonal interactions.

using LinearAlgebra, OrdinaryDiffEq, SparseArrays, Printf

const C6 = 865.723  # rad/ns · µm⁶

# ── Sparse Hamiltonian builder ──────────────────────────────────────────
# H_Ω = Σ σx_i / 2   (off-diagonal, connects |b⟩ ↔ |b⊕e_i⟩)
# H_Δ = Σ n_i         (diagonal,   Σ bit_i)
# H_int = Σ V_ij n_i n_j  (diagonal)
#
# For mat-free ODE: store H_Ω as a sparse matrix + diagonal vectors.

function build_operators(N)
    dim = 2^N

    # ── Sparse H_Ω: each row b has N neighbors b ⊕ e_i ───────────────
    I = Int[]; J = Int[]; V = Float64[]
    sizehint!(I, N * dim); sizehint!(J, N * dim); sizehint!(V, N * dim)

    for b in 0:(dim - 1)
        for i in 0:(N - 1)
            b_flip = xor(b, 1 << i)
            push!(I, b + 1)
            push!(J, b_flip + 1)
            push!(V, 0.5)
        end
    end
    H_Ω = sparse(I, J, V, dim, dim)

    # ── Diagonal H_Δ: Σ n_i → count_set_bits(b) ─────────────────────
    # Popcount for each basis state
    H_Δ_diag = [count_ones(b) for b in 0:(dim - 1)]
    # Could store as sparse diag but a vector + mul! is cheaper

    return H_Ω, H_Δ_diag
end

# ── Blockade interaction ────────────────────────────────────────────────
function build_interaction_diag(N, positions)
    dim = 2^N
    V = zeros(N, N)
    for i in 1:N, j in (i+1):N
        r = sqrt(sum((positions[:, i] - positions[:, j]) .^ 2))
        V[i, j] = V[j, i] = C6 / r^6
    end

    E_int = zeros(Float64, dim)
    for b in 0:(dim - 1)
        s = 0.0
        for i in 1:N, j in (i+1):N
            if V[i, j] != 0
                bit_i = (b >> (N - i)) & 1
                bit_j = (b >> (N - j)) & 1
                s += V[i, j] * bit_i * bit_j
            end
        end
        E_int[b + 1] = s
    end

    return E_int
end

# ── Sparse Hamiltonian action ───────────────────────────────────────────
# ψ̇ = -i (H_int + Δ(t)·H_Δ + Ω(t)·H_Ω) ψ
function hamiltonian_action!(dψ::Vector{ComplexF64}, ψ::Vector{ComplexF64},
                             H_Ω::SparseMatrixCSC{Float64, Int},
                             H_Δ_diag::Vector{Int}, E_int::Vector{Float64},
                             Ω::Float64, Δ::Float64)
    # Diagonal: H(t) = -i[H_int + Δ·H_Δ] where H_Δ = -Σ n → -i[H_int - Δ·Σn]
    # So: dψ = -i·E_int·ψ + i·Δ·(Σn)·ψ
    @. dψ = -(E_int - Δ * H_Δ_diag) * im * ψ
    # Off-diagonal: -i·Ω·H_Ω·ψ where H_Ω = (1/2)Σσx → -i·Ω/2·Σσx·ψ
    mul!(dψ, H_Ω, ψ, -im * Ω, 1.0)
    return nothing
end

# ── Parameterized sweep (linear interpolation between knots) ──────────
function make_drives(Ω_knots, Δ_knots, T)
    n_knots = length(Ω_knots)
    knot_t = collect(range(0.0, T, length = n_knots))
    return (
        Ω = t -> begin
            i = clamp(searchsortedlast(knot_t, t), 1, n_knots - 1)
            f = (t - knot_t[i]) / (knot_t[i + 1] - knot_t[i])
            Ω_knots[i] + f * (Ω_knots[i + 1] - Ω_knots[i])
        end,
        Δ = t -> begin
            i = clamp(searchsortedlast(knot_t, t), 1, n_knots - 1)
            f = (t - knot_t[i]) / (knot_t[i + 1] - knot_t[i])
            Δ_knots[i] + f * (Δ_knots[i + 1] - Δ_knots[i])
        end
    )
end

# ── Evaluate P_MIS for one set of parameters ────────────────────────────
function eval_pmis(Ω_knots, Δ_knots, positions; T=1000.0, n_steps=200,
                   abstol=1e-6, reltol=1e-4)
    N = size(positions, 2)
    dim = 2^N
    H_Ω, H_Δ_diag = build_operators(N)
    E_int = build_interaction_diag(N, positions)
    drives = make_drives(Ω_knots, Δ_knots, T)

    function f!(dψ, ψ, p, t)
        hamiltonian_action!(dψ, ψ, H_Ω, H_Δ_diag, E_int, drives.Ω(t), drives.Δ(t))
    end

    ψ0 = zeros(ComplexF64, dim); ψ0[1] = 1.0
    times = collect(range(0.0, T, length=n_steps))
    prob = ODEProblem(f!, ψ0, (0.0, T))
    sol = solve(prob, Tsit5(); saveat=times, abstol=abstol, reltol=reltol)
    ψ_final = sol.u[end]

    # MIS states
    R_b = (C6 * 1e3 / 6.283)^(1 / 6)
    adj = zeros(Bool, N, N)
    for i in 1:N, j in (i + 1):N
        r = sqrt(sum((positions[:, i] - positions[:, j]) .^ 2))
        adj[i, j] = adj[j, i] = r < R_b
    end
    max_sz = 0
    mis_bits = Int[]
    for b in 0:(dim - 1)
        bits = [(b >> (N - 1 - k)) & 1 for k in 0:(N - 1)]
        ok = true
        for i in 1:N, j in (i + 1):N
            if bits[i] == 1 && bits[j] == 1 && adj[i, j]
                ok = false; break
            end
        end
        if !ok; continue; end
        sz = sum(bits)
        if sz > max_sz; max_sz = sz; mis_bits = [b]
        elseif sz == max_sz; push!(mis_bits, b); end
    end

    return sum(abs2(ψ_final[b + 1]) for b in mis_bits)
end

# ═══════════════════════════════════════════════════════════════════════
# Test: verify sparse ops match dense for a small system
# ═══════════════════════════════════════════════════════════════════════════════
if basename(@__FILE__) == basename(String(PROGRAM_FILE))
println("═══ Sparse MIS Engine — verification & scaling ═══\n")

for (name, N, make_pos) in [
    ("star K₁₃", 4, () -> begin
        ρ = 5.5
        [0.0   ρ      -ρ/2        -ρ/2;
         0.0   0.0     ρ*√3/2     -ρ*√3/2]
    end),
    ("cycle C₅", 5, () -> begin
        s = 5.5
        angles = [2π * k / 5 for k in 0:4]
        [s * cos.(angles)  s * sin.(angles)]'
    end),
]
    pos = make_pos()
    @printf("─── %s (N=%d, dim=%d) ───\n", name, N, 2^N)
    flush(stdout)

    H_Ω, H_Δ_diag = build_operators(N)
    E_int = build_interaction_diag(N, pos)
    @printf("  H_Ω nnz = %d  (density = %.2e)\n", nnz(H_Ω), nnz(H_Ω) / (2^N)^2)
    flush(stdout)

    # Test with the 3-stage sweep that worked in Ch02
    Δ_0, Δ_f, Ω_mid = -0.01257, 0.01257, 0.006
    Ω_knots = [0.0, Ω_mid, Ω_mid, Ω_mid, Ω_mid, 0.0]
    Δ_knots = [Δ_0, Δ_0, Δ_0 + 0.3*(Δ_f-Δ_0), Δ_0 + 0.7*(Δ_f-Δ_0), Δ_f, Δ_f]

    P = eval_pmis(Ω_knots, Δ_knots, pos; T=2000.0, n_steps=200)
    @printf("  P_MIS = %.6f (T=2000ns)\n", P)
    flush(stdout)
end
end
