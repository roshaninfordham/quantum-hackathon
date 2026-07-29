using LinearAlgebra, OrdinaryDiffEq, SparseArrays, Printf

const C6 = 865.723
const σx = ComplexF64[0 1; 1 0]; const n_op = ComplexF64[0 0; 0 1]; const I2 = ComplexF64[1 0; 0 1]
embed(op, i, N) = foldl(kron, [j == i ? op : I2 for j in 1:N])

function run_verify()
    ρ = 5.5; pos = [0.0   ρ      -ρ/2        -ρ/2; 0.0   0.0     ρ*√3/2     -ρ*√3/2]
    N = 4; dim = 2^N

    # Dense operators
    H_Ω_d = sum(embed(σx, i, N) for i in 1:N) / 2
    H_Δ_d = -sum(embed(n_op, i, N) for i in 1:N)
    H_int_d = zeros(ComplexF64, dim, dim)
    for i in 1:N, j in (i+1):N
        r = sqrt(sum((pos[:,i]-pos[:,j]).^2))
        H_int_d += (C6/r^6) * embed(n_op,i,N) * embed(n_op,j,N)
    end

    # Sparse H_Ω
    I,J,V = Int[], Int[], Float64[]
    for b in 0:dim-1; for i in 0:N-1; push!(I,b+1); push!(J,xor(b,1<<i)+1); push!(V,0.5); end; end
    H_Ω_s = sparse(I,J,V,dim,dim)

    H_Δ_s_diag = Float64[count_ones(b) for b in 0:dim-1]
    V_mut = zeros(N,N)
    for i in 1:N, j in (i+1):N
        r = sqrt(sum((pos[:,i]-pos[:,j]).^2))
        V_mut[i,j] = V_mut[j,i] = C6/r^6
    end
    E_int = zeros(Float64, dim)
    for b in 0:dim-1
        s = 0.0
        for i in 1:N, j in (i+1):N
            bit_i = (b >> (N - i)) & 1
            bit_j = (b >> (N - j)) & 1
            s += V_mut[i,j] * bit_i * bit_j
        end
        E_int[b+1] = s
    end

    # Compare H·ψ
    ψ = randn(ComplexF64, dim); ψ /= norm(ψ)
    for (Ω_val, Δ_val) in [(0.006, 0.0), (0.006, -0.01257), (0.006, 0.01257)]
        d_dense = -im * (H_int_d + Ω_val * H_Ω_d + Δ_val * H_Δ_d) * ψ
        d_sparse = similar(ψ)
        @. d_sparse = -(E_int - Δ_val * H_Δ_s_diag) * im * ψ
        mul!(d_sparse, H_Ω_s, ψ, -im * Ω_val, 1.0)
        @printf("  H·ψ diff Ω=%.6f Δ=%.6f: %.2e\n", Ω_val, Δ_val, maximum(abs.(d_dense - d_sparse)))
    end

    # Compare full sweep
    function make_solver(H_int, H_Ω_op, H_Δ_op, diag_mode)
        Ω0 = 0.006; Δ0 = -0.01257; Δf = 0.01257
        Ω_knots = [0.0, Ω0, Ω0, Ω0, Ω0, 0.0]
        Δ_knots = [Δ0, Δ0, Δ0+0.3*(Δf-Δ0), Δ0+0.7*(Δf-Δ0), Δf, Δf]
        n_knots = 6; knot_t = collect(range(0.0, 4000.0, length=n_knots))
        return function(T)
            t_knots = collect(range(0.0, T, length=n_knots))
            function f!(dψ, ψ, p, t)
                i = clamp(searchsortedlast(t_knots, t), 1, n_knots-1)
                f = (t - t_knots[i]) / (t_knots[i+1] - t_knots[i])
                Ω = Ω_knots[i] + f * (Ω_knots[i+1] - Ω_knots[i])
                Δ = Δ_knots[i] + f * (Δ_knots[i+1] - Δ_knots[i])
                if diag_mode == :dense
                    dψ .= -im * (H_int + Ω * H_Ω_op + Δ * H_Δ_op) * ψ
                else
                    @. dψ = -(E_int - Δ * H_Δ_s_diag) * im * ψ
                    mul!(dψ, H_Ω_s, ψ, -im * Ω, 1.0)
                end
            end
            ψ0 = zeros(ComplexF64, dim); ψ0[1] = 1.0
            times = collect(range(0.0, T, length=200))
            sol = solve(ODEProblem(f!, ψ0, (0.0, T)), Tsit5(); saveat=times, abstol=1e-8, reltol=1e-6)
            R_b = (C6*1e3/6.283)^(1/6)
            adj = zeros(Bool,N,N)
            for i in 1:N, j in (i+1):N; r=sqrt(sum((pos[:,i]-pos[:,j]).^2)); adj[i,j]=adj[j,i]=r<R_b; end
            max_sz=0; mis_bits=Int[]
            for b in 0:dim-1
                bits=[(b>>(N-1-k))&1 for k in 0:N-1]; ok=true
                for i in 1:N, j in (i+1):N; if bits[i]==1&&bits[j]==1&&adj[i,j]; ok=false;break;end;end
                if !ok; continue; end; sz=sum(bits)
                if sz>max_sz; max_sz=sz; mis_bits=[b]; elseif sz==max_sz; push!(mis_bits,b); end
            end
            return sum(abs2(sol.u[end][b+1]) for b in mis_bits)
        end
    end

    dense_f = make_solver(H_int_d, H_Ω_d, H_Δ_d, :dense)
    sparse_f = make_solver(nothing, nothing, nothing, :sparse)

    println("\n─── Sweep P_MIS ───")
    for T in [500.0, 1000.0, 2000.0, 4000.0]
        Pd = dense_f(T); Ps = sparse_f(T)
        @printf("  T=%.0f: dense=%.6f sparse=%.6f diff=%.2e\n", T, Pd, Ps, abs(Pd-Ps))
    end
end

run_verify()
