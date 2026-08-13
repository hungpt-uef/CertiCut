# CertiCut Phase 0 Report

Ngày: 10/08/2026

## Trạng thái

PASS. Đã hoàn tất foundation validation trước Phase 1.

## Môi trường

- Python `3.11.9`
- Venv: `.venv`
- `qiskit==2.5.1`
- `qiskit-addon-cutting==0.10.0`
- `pytest==8.4.2`

Kích hoạt PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Tái lập toàn bộ:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\run_phase0.py
```

## Kết quả QPD gate cutting

Mô hình: CNOT decomposition từ Qiskit addon, exact quasiprobability evaluation (`num_samples=inf`), exact statevector sampler.

| CNOT cuts | QPD overhead | Kỳ vọng | `<Z...Z>` uncut | `<Z...Z>` reconstructed | Subexperiments/fragment |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 9 | 9 | 0.9999999999999998 | 0.9999999999999996 | 6 |
| 2 | 81 | 81 | 0.9999999999999996 | 0.9999999999999988 | 36 |

Sai số reconstruction dưới `1e-12`, thuộc floating-point precision. Kết quả xác nhận objective V1 cho CNOT độc lập:

```text
Gamma = 9^k
log_cost = log(Gamma)
```

## Toy Ground Truth: 6 qubit

Circuit gồm các CNOT:

```text
(q0,q1), (q1,q2), (q3,q4), (q4,q5), (q1,q4), (q2,q3)
```

Ràng buộc: `Qmax=3`, đúng hai fragments. Brute force mọi partition hợp lệ, cố định `q0` ở fragment đầu để loại symmetry trùng lặp.

| Thuộc tính | Kết quả |
| --- | --- |
| Partition tối ưu | `{q0,q1,q2}`, `{q3,q4,q5}` |
| Cross-fragment CNOT | instruction index `4`, `5` |
| Số cuts | `2` |
| Gamma / UB | `81` |
| Objective / log-cost | `4.394449154672439 = log(81)` |

Brute force là ground truth Phase 0. Chưa có LP relaxation nên chưa được ghi `LB`, `gap`, hay `PROVEN OPTIMAL` theo certificate B&B; đó là Phase 2-3.

## Files

- `requirements.txt`: dependency pin.
- `certicut/circuits/phase0.py`: circuits, QPD validation, brute-force solver.
- `scripts/run_phase0.py`: xuất raw result.
- `tests/test_phase0.py`: 3 regression tests.
- `results/phase0_summary.json`: raw deterministic output.

## Verification

```text
3 passed in 0.61s
```

## Scope

Phase 0 chỉ xác minh ideal/exact CNOT gate cuts, independent overhead, hai fragments, toy 6-qubit. Không có sampling noise, wire cuts, automated cut finder, graph model, MILP, B&B, certificate, hay GNN.

`ponytail:` independent-CNOT cost is V1 ceiling; upgrade objective only after Phase 3 correctness when joint-QPD costs become required.

## Next

Phase 1: interaction graph, aggregate two-qubit gate weights, depth statistics, unit tests.
