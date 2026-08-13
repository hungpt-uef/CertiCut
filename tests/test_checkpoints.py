from certicut.benchmark.checkpoints import extract_checkpoints
from certicut.circuits.phase0 import make_six_qubit_toy_circuit
from certicut.graph.interaction import build_interaction_graph
from certicut.optimization.bnb import solve_certified_bnb


def test_checkpoint_root_and_forward_fill_are_safe_and_monotonic() -> None:
    result = solve_certified_bnb(
        build_interaction_graph(make_six_qubit_toy_circuit()), qmax=3, lp_variant="b2s_root", warm_start_variant="h2"
    )
    checkpoints = extract_checkpoints(result, (0, 1, 5))
    assert checkpoints[0].expanded_nodes == 0
    assert [checkpoint.lb_log for checkpoint in checkpoints] == sorted(checkpoint.lb_log for checkpoint in checkpoints)
    assert [checkpoint.ub_log for checkpoint in checkpoints] == sorted((checkpoint.ub_log for checkpoint in checkpoints), reverse=True)
    assert all(checkpoint.lb_log <= checkpoint.ub_log + 1e-10 for checkpoint in checkpoints)
