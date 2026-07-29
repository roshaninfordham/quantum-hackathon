using LinearAlgebra, OrdinaryDiffEq, SparseArrays, Printf

const C6 = 865.723
const σx = ComplexF64[0 1; 1 0]; const n_op = ComplexF64[0 0; 0 1]; const I2 = ComplexF64[1 0; 0 1]
embed(op, i, N) = foldl(kron, [j == i ? op : I2 for j in 1:N])

function debug()
    ρ = 5.5; pos = [0.0   ρ      -ρ/2        -ρ/2; 0.0   0.0     ρ*√3/2     -ρ*√3/2]
    N = 4; dim = 2^N

    # Dense
    H_Ω_d = sum(embed(σx, i, N) for i in 1:N) / 2
    H_Δ_d = -sum(embed(n_op, i, N) for i in 1:N)
    H_int_d = zeros(ComplexF64, dim, dim)
    for i in 1:N, j in (i+1):N
        r = sqrt(sum((pos[:,i]-pos[:,j]).^2))
        H_int_d += (C6/r^6) * embed(n_op,i,N) * embed(n_op,j,N)
    end

    # Sparse
    I,J,V = Int[], Int[], Float64[]
    for b in 0:dim-1; for i in 0:N-1; push!(I,b+1); push!(J,xor(b,1<<i)+1); push!(V,0.5); end; end
    H_Ω_s = sparse(I,J,V,dim,dim)

    H_Δ_s_diag = Float64[count_ones(b) for b in 0:dim-1]

    V_mut = zeros(N,N)
    for i in 1:N, j in (i+1):N
        r = sqrt(sum((pos[:,i]-pos[:,j]).^2))
        V_mut[i,j] = V_mut[j,i] = C6/r^6
    end

    # Compare E_int computation
    # Method A: from dense diagonal
    E_dense = real.(diag(H_int_d))
    # Method B: direct computation
    E_direct = zeros(Float64, dim)
    for b in 0:dim-1
        s = 0.0
        for i in 1:N, j in (i+1):N
            bit_i = (b >> (N - i)) & 1
            bit_j = (b >> (N - j)) & 1
            s += V_mut[i,j] * bit_i * bit_j
        end
        E_direct[b+1] = s
    end

    println("E_int max diff (dense vs direct): ", maximum(abs.(E_dense - E_direct)))

    # Compare H_Ω mat-vec
    ψ = randn(ComplexF64, dim); ψ /= norm(ψ)
    HΩψ_d = H_Ω_d * ψ
    HΩψ_s = H_Ω_s * ψ
    println("H_Ω max diff: ", maximum(abs.(HΩψ_d - HΩψ_s)))

    # Compare full H·ψ: H = H_int + Ω*H_Ω + Δ*H_Δ
    Ω_val, Δ_val = 0.006, -0.01257
    H_ψ_d = (H_int_d + Ω_val * H_Ω_d + Δ_val * H_Δ_d) * ψ
    diag_E = E_direct + Δ_val * H_Δ_s_diag
    H_ψ_s = zero(ψ)
    @. H_ψ_s = (E_direct + Δ_val * H_Δ_s_diag) * ψ
    H_ψ_s += Ω_val * (H_Ω_s * ψ)
    println("H·ψ (full) max diff: ", maximum(abs.(H_ψ_d - H_ψ_s)))

    # Check individual components
    H_int_ψ_d = H_int_d * ψ
    H_int_ψ_s = E_direct .* ψ
    println("H_int·ψ max diff: ", maximum(abs.(H_int_ψ_d - H_int_ψ_s)))

    H_Δ_ψ_d = H_Δ_d * ψ
    H_Δ_ψ_s = (-H_Δ_s_diag) .* ψ  # H_Δ_d = -Σn
    println("H_Δ·ψ max diff: ", maximum(abs.(H_Δ_ψ_d - H_Δ_ψ_s)))

    H_Ω_ψ_d = H_Ω_d * ψ
    H_Ω_ψ_s = H_Ω_s * ψ
    println("H_Ω·ψ max diff: ", maximum(abs.(H_Ω_ψ_d - H_Ω_ψ_s)))

    # Show a few elements for comparison
    idxs = [1, 2, 5, 9]
    println("\nSample elements (states |0000⟩, |0001⟩, |0100⟩, |1000⟩):")
    for idx in idxs
        println("  ψ[$idx] = $(ψ[idx])")
        println("    dense HΩψ = $(HΩψ_d[idx]), sparse HΩψ = $(HΩψ_s[idx])")
        println("    dense H_int_ψ = $(H_int_ψ_d[idx]), sparse = $(H_int_ψ_s[idx])")
    end
end

debug()
