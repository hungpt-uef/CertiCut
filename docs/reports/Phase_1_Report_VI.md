# CertiCut Phase 1 Report

Ngày: 10/08/2026

## Trạng thái

PASS. `QuantumCircuit -> InteractionGraph -> weighted partition objective` đã được kiểm chứng trước Phase 2.

## Representation

`InteractionGraph` là dataclass thuần Python, không thêm NetworkX/PyG vì Phase 1 chưa cần traversal hay ML framework.

- Node: mọi qubit `0..circuit.num_qubits-1`, kể cả qubit cô lập.
- Edge: một edge vô hướng canonical `(min(u,v), max(u,v))` cho mỗi cặp qubit có ít nhất một two-qubit gate.
- Aggregate: nhiều gate cùng pair chỉ tạo một edge.
- Raw trace: `instruction_index`, `layer_depth`, `gate_type`, `control`, `target` được giữ cho từng gate.
- Layer depth: dependency-aware greedy layer, riêng với `instruction_index` trong `qc.data`.

V1 QPD mapping:

```text
cx: rho = 9
w(u,v) = sum(log(rho_g)) for every gate g on edge (u,v)
J(P) = sum(w(u,v) for crossed edges)
```

Unsupported two-qubit gate fail-fast bằng `ValueError`; không được âm thầm gán CNOT cost cho gate khác.

## Toy Results

Input Phase 0:

```text
(q0,q1), (q1,q2), (q3,q4), (q4,q5), (q1,q4), (q2,q3)
```

Output:

| Thuộc tính | Kết quả |
| --- | --- |
| Nodes | `6` |
| Edges | `6` |
| Mỗi edge | `gate_count=1`, `qpd_log_cost=log(9)` |
| Partition `{0,1,2}` / `{3,4,5}` | `J(P)=log(81)=4.394449154672439` |
| Feasible `Qmax=3` partitions, symmetry-reduced | `10` |
| Gate-level objective = graph-level objective | tất cả `10/10` |

## Regression Coverage

- Toy topology, edge set, costs, raw cross-edge metadata.
- Aggregate `CX(0,1), CX(1,0), CX(0,1)` thành một edge, `gate_count=3`, cost `3*log(9)`.
- Single-qubit gates không tạo edge.
- Isolated qubits còn trong node set.
- Exhaustive objective equivalence trên mọi valid toy partition.
- Deterministic dataclass serialization.

## Files

- `certicut/graph/interaction.py`: graph, cost mapping, objectives, partition enumerator.
- `certicut/graph/features.py`: exports node/edge feature types.
- `tests/test_interaction_graph.py`: 5 Phase 1 tests.
- `scripts/run_phase1.py`: serialization runner.
- `results/phase1_graph_summary.json`: raw deterministic graph output.

## Verification

```text
8 passed in 0.63s
```

Tái lập:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\run_phase1.py
```

## Scope

Không có MILP, LP relaxation, B&B, LB/UB certificate, automated cut finder, PyTorch, hay GNN. Graph hiện xử lý CNOT-only V1; mixed/gate-specific QPD overhead là extension sau khi exact formulation đúng.

`ponytail:` dataclass graph ceiling is Phase 1/2 prototype; adopt NetworkX only when algorithms actually need its graph operations, PyG only at Phase 6.

## Next

Phase 2: formulation assignment/cut variables, capacity constraints, objective từ `qpd_log_cost`, exact validation đối chiếu brute force.
