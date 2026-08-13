# CertiCut Phase 2 Report

Ngày: 10/08/2026

## Trạng thái

PASS. Exact MILP formulation khớp brute-force ground truth trước Phase 3.

## Solver

- `scipy==1.17.1`, `scipy.optimize.milp`
- HiGHS open-source MILP backend
- CNOT-only V1 weighted interaction graph từ Phase 1

Biến:

```text
y[i,p] = 1 iff qubit i belongs to fragment p
x[e]   = 1 iff edge e crosses two fragments
```

Ràng buộc:

```text
sum_p y[i,p] = 1
sum_i y[i,p] <= Qmax
sum_i y[i,p] >= 1                 only exact_num_fragments=True
x[i,j] >= y[i,p] - y[j,p]
x[i,j] >= y[j,p] - y[i,p]
y[0,0] = 1                        symmetry break
```

Objective:

```text
min sum(w[i,j] * x[i,j])
w[i,j] = edge.qpd_log_cost
```

`objective_log_cost` là source of truth. `gamma=exp(objective_log_cost)` chỉ display field; trả `null` khi overflow. Sai số `81.00000000000003` là floating-point expansion của `exp(log(81))`.

## Semantics

- `exact_num_fragments=False`: dùng at most `K` fragments; empty fragment hợp lệ.
- `exact_num_fragments=True`: dùng exactly `K` non-empty fragments.
- Tổng capacity thiếu (`n > K*Qmax`) hoặc exact-K đòi nhiều fragment hơn qubit trả `status="infeasible"` trước solver.

## Toy Result

Input: Phase 0 six-qubit circuit, `K=2`, `Qmax=3`, `exact_num_fragments=true`.

| Thuộc tính | Kết quả |
| --- | --- |
| Status | `optimal` |
| Partition | `{0,1,2}` / `{3,4,5}` |
| Cut edges | `(1,4)`, `(2,3)` |
| Cut instruction indices | `4`, `5` |
| Objective | `log(81)=4.394449154672439` |
| Gamma display | `81.00000000000003` |
| Brute force | khớp chính xác |

Raw artifact: `results/phase2_exact_summary.json`.

## Regression Coverage

- Handbook toy optimum, canonical partition, cuts, executable instruction trace.
- Aggregated `3*CX(0,1)` forced cut: `3*log(9)=log(729)`.
- At-most-K zero-cut case và exactly-K non-empty semantics.
- Infeasible capacity clean result, không fake partition.
- Isolated qubits vẫn được assign đúng capacity.
- Deterministic repeat solve; `q0` luôn fragment `0`.
- `100` seeded random CNOT circuits (`n=4..8`) MILP optimum khớp brute-force optimum 100%.

## Files

- `certicut/optimization/exact.py`: SciPy/HiGHS MILP, solution model, brute-force oracle.
- `tests/test_exact_partition.py`: 7 Phase 2 regression tests.
- `scripts/run_phase2.py`: toy exact solver runner.
- `results/phase2_exact_summary.json`: raw deterministic output.
- `requirements.txt`: pinned SciPy dependency.

## Verification

```text
15 passed in 1.86s
```

Tái lập:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\run_phase2.py
```

## Scope

Phase 2 là exact MILP optimum, không expose CertiCut lower bound, upper bound, gap, timeout behavior, custom B&B, or learned policy. Symmetry break `y[0,0]=1` canonicalize two-fragment V1; stronger multi-fragment symmetry breaking cần trước large-`K` experiments.

`ponytail:` SciPy/HiGHS direct solve ceiling is Phase 2 validation; Phase 3 must own LP-relaxation nodes, global LB, incumbent UB, pruning, timeout, and certificate API.

## Next

Phase 3: LP relaxation + Branch-and-Bound, maintain `LB <= OPT <= UB` under time budget.
