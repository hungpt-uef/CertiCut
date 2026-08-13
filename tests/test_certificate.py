from math import exp, isclose, log

from certicut.optimization.certificate import make_certificate


def test_certificate_uses_additive_log_gap_and_overhead_factor() -> None:
    certificate = make_certificate(4.5, 4.6)
    assert isclose(certificate.additive_log_gap, 0.1, abs_tol=1e-12)
    assert isclose(certificate.overhead_factor_bound or 0, exp(0.1), abs_tol=1e-12)
    assert not certificate.proven_optimal


def test_equal_bounds_are_proven_optimal() -> None:
    certificate = make_certificate(log(81), log(81))
    assert certificate.proven_optimal
    assert certificate.overhead_factor_bound == 1.0
    assert certificate.formal_numerical_proof


def test_solver_tolerance_report_exposes_declared_conservative_margin() -> None:
    certificate = make_certificate(
        4.5, 4.6, certificate_kind="solver_tolerance", numerical_safety_margin_log=0.01
    )
    assert not certificate.formal_numerical_proof
    assert certificate.conservative_lower_bound_log == 4.49
    assert certificate.conservative_overhead_factor_bound is not None
    assert certificate.conservative_overhead_factor_bound > certificate.overhead_factor_bound
