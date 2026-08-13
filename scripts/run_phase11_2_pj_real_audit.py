"""Small real-circuit PJ-QPD relevance audit with exact pattern MILP."""
from __future__ import annotations
import json
from math import pi
from pathlib import Path
import mqt.bench as mqt
from qiskit import transpile
from certicut.optimization.parallel_joint import exact_balanced_partitions, evaluate_parallel_joint_partition, parallel_layer_gates
from certicut.optimization.pj_exact import solve_exact_pj_pattern_milp

ROOT=Path(__file__).resolve().parents[1]
def independent_opt(circuit):
    return min(((p,evaluate_parallel_joint_partition(circuit,p)) for p in exact_balanced_partitions(circuit.num_qubits)),key=lambda x:(x[1].independent_log_cost,x[0]))
def main():
    records=[]
    for family in ("qaoa","vqe_real_amp","bv"):
        for n in (8,12):
            try:
                circuit=mqt.get_benchmark_alg(family,n,random_parameters=False)
                if circuit.parameters:
                    circuit=circuit.assign_parameters({parameter:pi/4 for parameter in circuit.parameters},inplace=False)
                if family!="qaoa": circuit=transpile(circuit,basis_gates=["rz","sx","x","cx"],optimization_level=0)
                if circuit.num_qubits%2: continue
                p_ind,e_ind=independent_opt(circuit)
                pj=solve_exact_pj_pattern_milp(circuit,time_limit_s=60)
                pj_at_ind=evaluate_parallel_joint_partition(circuit,p_ind)
                strict=pj.objective_log_cost is not None and pj_at_ind.parallel_joint_log_cost>(pj.objective_log_cost+1e-9)
                records.append({"family":family,"n":n,"two_qubit_gates":len(parallel_layer_gates(circuit)),"independent_partition":p_ind,"pj_partition":pj.partition,"independent_log_opt":e_ind.independent_log_cost,"pj_log_at_independent_opt":pj_at_ind.parallel_joint_log_cost,"pj_log_opt":pj.objective_log_cost,"regret_factor":pj_at_ind.parallel_joint_overhead/(pj.overhead or 1.0),"strict_reversal":strict,"status":pj.status})
                print(f"[{family} n={n}] rev={strict} F={records[-1]['regret_factor']:.6f}")
            except Exception as error:
                records.append({"family":family,"n":n,"status":"error","error":repr(error)})
                print(f"[{family} n={n}] error {error}")
    p=ROOT/"results"/"phase11_2_pj_real_audit.json";p.write_text(json.dumps(records,indent=2)+"\n");print(f"Wrote {p}")
if __name__=="__main__":main()
