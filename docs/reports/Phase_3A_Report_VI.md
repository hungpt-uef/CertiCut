# CertiCut Phase 3A Report

Ngày: 10/08/2026

## Trạng thái

PASS. CertiCut có certified anytime Branch-and-Bound cho CNOT-only, hai fragments.

## Scope

- `K=2` only.
- CNOT-only weighted interaction graph.
- LP relaxation, deterministic greedy primal warm start, best-bound B&B, most-fractional branching.
- `node_limit` deterministic; `time_limit_s` chỉ kiểm ở safe checkpoint giữa node expansions.
- Không GNN, strong branching, cutting planes, wire/mixed cuts, noise, hay `K>2`.

## Certificate

Mỗi unresolved node giữ LP lower bound. Global bound:

```text
LB = min(incumbent UB, min(LB(node) for node in frontier))
UB = objective của incumbent feasible partition
LB <= OPT <= UB
Delta_log = UB - LB
overhead_factor_bound = exp(Delta_log)
```

`Delta_log` là source-of-truth gap. `overhead_factor_bound` diễn giải: sampling overhead incumbent không quá factor đó lần optimum. `proven_optimal=true` chỉ khi frontier rỗng và `LB=UB` trong tolerance.

## Safe Timeout Invariant

Node popped không bị bỏ quên: B&B hoàn tất LP của cả hai child, đưa mọi child chưa prune vào frontier, rồi mới tăng expanded-node/check budget tiếp theo. Khi `node_limit=0` hoặc `time_limit_s=0`, root chưa bị pop nên root LB vẫn trong frontier certificate.

## Toy Result

Input: 6-qubit handbook toy, `K=2`, `Qmax=3`, exact-K.

| Thuộc tính | Kết quả |
| --- | --- |
| Status | `optimal` |
| Expanded nodes | `2` |
| Partition | `{0,1,2}` / `{3,4,5}` |
| Cut edges | `(1,4)`, `(2,3)` |
| Instruction indices | `4`, `5` |
| Root LP LB | `1.3183347464017316` |
| Final LB = UB | `log(81)=4.394449154672439` |
| Additive log gap | `0` |
| Certified overhead factor | `1.0` |

Root relaxation loose là expected: fractional assignments cho phép reduced cross-edge cost. B&B vẫn exact/certified vì LP relaxation là lower bound hợp lệ.

## Validation

- LP `<=` Phase 2 MILP optimum trên `100/100` seeded random circuits.
- B&B completion `LB=UB=MILP OPT` trên `100/100` seeded random circuits, `n=4..8`.
- Node-limit certificate `LB<=MILP OPT<=UB` trên `30/30` seeded random circuits.
- `UB` non-increasing, global `LB` non-decreasing trong node-limit traces.
- Zero-time limit preserves root LP bound.
- Infeasible root handled cleanly.
- Node-limit runs deterministic.
- Phase 0-2 regression còn pass.

## Files

- `certicut/optimization/lp.py`: K=2 LP relaxation bound oracle.
- `certicut/optimization/heuristics.py`: deterministic greedy feasible warm start.
- `certicut/optimization/certificate.py`: log-domain certificate and factor conversion.
- `certicut/optimization/bnb.py`: safe-checkpoint vanilla best-bound B&B.
- `tests/test_lp_relaxation.py`: LP validity corpus.
- `tests/test_certificate.py`: certificate math.
- `tests/test_bnb.py`: B&B/oracle/timeout invariants.
- `scripts/run_phase3.py`: toy execution plus JSON/JSONL artifacts.
- `results/phase3_summary.json`: final result.
- `results/phase3_timeline.jsonl`: plot-ready bound events.

## Verification

```text
25 passed in 5.37s
```

Tái lập:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\run_phase3.py
```

## Next

Phase 3B: strengthen relaxation/warm start/branching only after profiling node counts and gap quality. Phase 4: Qiskit baseline integration.

`ponytail:` K=2 B&B is Phase 3A correctness ceiling; generalize node assignment and symmetry rules to K>2 only after Phase 3B invariants remain proven.
