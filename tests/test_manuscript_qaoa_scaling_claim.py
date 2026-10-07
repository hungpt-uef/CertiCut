from __future__ import annotations

import pytest

from certicut.circuits.ingestion import ingest_mqt_pair
from certicut.graph.interaction import build_interaction_graph


def _weights(circuit):
    graph = build_interaction_graph(circuit, cost_model="qiskit_qpd")
    return {(edge.u, edge.v): edge.qpd_log_cost for edge in graph.edges}


@pytest.mark.parametrize("n", [4, 6, 8, 10, 12, 14, 16])
def test_fixed_pi_over_four_qaoa_weights_are_uniform_positive_scaling(n: int) -> None:
    pair = ingest_mqt_pair("qaoa", n)
    cx, _ = pair["cx_normalized"]
    native, _ = pair["native_qpd"]
    a = _weights(cx)
    b = _weights(native)
    assert set(a) == set(b)
    ratios = [a[e] / b[e] for e in sorted(a) if b[e] > 0]
    assert ratios
    assert min(ratios) > 0
    assert max(ratios) - min(ratios) <= 1e-10
    assert ratios[0] == pytest.approx(2.0)
