#!/usr/bin/env julia
# N=20 with sparse matrix CSR direct construction (no triplets)
using LinearAlgebra, SparseArrays, Printf, Random
Random.seed!(42)

const C6 = 865.723; const Δ_RANGE = 0.01257

N = 20; L = 30.0
positions = L * rand(2, N)
dim = 2^N

# diag ops
H_Δ_diag = Float64[count_ones(b) for b in 0:(dim-1)]
V_mat = zeros(N, N)
for i in 1:N, j in (i+1):N
    r = sqrt(sum((positions[:,i] - positions[:,j]) .^ 2))
    V_mat[i,j] = V_mat[j,i] = C6 / r^6
end
E_int = zeros(Float64, dim)
for b in 0:(dim-1)
    s = 0.0
    for i in 1:N, j in (i+1):N
        V_mat[i,j] != 0 && (s += V_mat[i,j] * ((b>>(N-i))&1) * ((b>>(N-j))&1))
    end
    E_int[b+1] = s
end
bit_masks = [1 << (N-i) for i in 1:N]

# Build H_Ω as SparseMatrixCSC directly (no triplets!)
@printf("Building H_Ω (CSR direct, %d x %d)... ", dim, dim); flush(stdout)
@time begin
    nnz_per_row = N
    nnz_total = dim * nnz_per_row
    rowptr = Vector{Int}(undef, dim + 1)
    colval = Vector{Int}(undef, nnz_total)
    nzval = Vector{Float64}(undef, nnz_total)
    for i in 1:dim+1
        rowptr[i] = (i - 1) * nnz_per_row + 1
    end
    for b in 0:(dim-1)
        base = b * N
        @inbounds for (j, mask) in enumerate(bit_masks)
            colval[base + j] = xor(b, mask) + 1
            nzval[base + j] = 0.5
        end
    end
    H_Ω = SparseMatrixCSC(dim, dim, rowptr, colval, nzval)
end
@printf("  nnz=%d\n", nnz(H_Ω))
flush(stdout)

# single apply_H! via sparse mul! + diagonal
function apply_H!(dψ, ψ, Ω, Δ)
    # diagonal
    @inbounds @simd for b in 1:dim
        dψ[b] = -im * (E_int[b] - Δ * H_Δ_diag[b]) * ψ[b]
    end
    # off-diagonal via sparse mul!
    mul!(dψ, H_Ω, ψ, -im * Ω, one(ComplexF64))
end

ψ = zeros(ComplexF64, dim); ψ[1] = 1.0
dψ = similar(ψ)

# warm-up & time
@printf("apply_H! warm-up... "); flush(stdout)
GC.gc(); @time apply_H!(dψ, ψ, 0.006, 0.0)
@printf("  done\n"); flush(stdout)

@printf("apply_H! timed (10 calls)... "); flush(stdout)
GC.gc(); @time for _ in 1:10; apply_H!(dψ, ψ, 0.006, 0.0); end
@printf("  done\n"); flush(stdout)
