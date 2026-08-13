"""Phase 11.2A root-polyhedral decomposition on circuit-derived tail strata."""
from __future__ import annotations
import json
from dataclasses import asdict
from pathlib import Path
from certicut.circuits.benchmarks import make_benchmark_circuit
from certicut.graph.interaction import build_interaction_graph
from certicut.optimization.core_root_lp import solve_core_root_lp
from certicut.optimization.bnb import solve_certified_bnb

ROOT=Path(__file__).resolve().parents[1]
def main():
    records=[]
    for family in ("random","dense","weighted_random","noisy_community"):
        # Full all-violated triangle closure at n=40 exceeded the 10-minute
        # audit budget. Keep this component-isolation rung fully completed.
        for n in (16,24):
            for seed in range(3):
                graph=build_interaction_graph(make_benchmark_circuit(family,n,seed))
                oracle=solve_certified_bnb(graph,qmax=n//2,exact_num_fragments=True,lp_variant="b2s_root",warm_start_variant="h2",time_limit_s=60)
                opt=oracle.certificate.upper_bound_log if oracle.certificate and oracle.certificate.proven_optimal else None
                for variant in ("b0","cardinality","triangles","b2s"):
                    result=solve_core_root_lp(graph,variant=variant,max_rounds=20)
                    payload=asdict(result)
                    payload.pop("x_values",None)
                    records.append({"family":family,"n":n,"seed":seed,"opt":opt,**payload})
                    print(f"[{family} n={n} s={seed} {variant}] lb={result.lower_bound:.4f} cuts={len(result.active_triangles)}")
    p=ROOT/"results"/"phase11_2_root_tail.json";p.write_text(json.dumps(records,indent=2)+"\n");print(f"Wrote {p}")
if __name__=="__main__":main()
