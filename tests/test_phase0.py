from math import isclose, log

from certicut.circuits.phase0 import (
    brute_force_two_fragment_plan,
    make_six_qubit_toy_circuit,
    reconstruct_cut_z_expectation,
)


def test_one_cnot_cut_has_overhead_nine_and_correct_reconstruction() -> None:
    result = reconstruct_cut_z_expectation(1)
    assert result["qpd_overhead"] == 9.0
    assert result["expected_overhead"] == 9.0
    assert isclose(result["uncut_z_expectation"], 1.0, abs_tol=1e-12)
    assert isclose(result["reconstructed_z_expectation"], 1.0, abs_tol=1e-12)
    assert isclose(result["reconstructed_z_expectation"], result["uncut_z_expectation"], abs_tol=1e-12)


def test_two_cnot_cuts_have_overhead_eighty_one_and_correct_reconstruction() -> None:
    result = reconstruct_cut_z_expectation(2)
    assert result["qpd_overhead"] == 81.0
    assert result["expected_overhead"] == 81.0
    assert isclose(result["uncut_z_expectation"], 1.0, abs_tol=1e-12)
    assert isclose(result["reconstructed_z_expectation"], 1.0, abs_tol=1e-12)
    assert isclose(result["reconstructed_z_expectation"], result["uncut_z_expectation"], abs_tol=1e-12)


def test_six_qubit_brute_force_matches_handbook_plan() -> None:
    plan = brute_force_two_fragment_plan(make_six_qubit_toy_circuit(), qmax=3)
    assert plan.fragments == ((0, 1, 2), (3, 4, 5))
    assert plan.cut_gate_indices == (4, 5)
    assert plan.gamma == 81.0
    assert isclose(plan.log_cost, log(81.0), abs_tol=1e-12)
