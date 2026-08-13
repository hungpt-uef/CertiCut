from decimal import Decimal, localcontext

from certicut.optimization.intervals import conservative_factor, log_overhead_interval


def test_log_interval_encloses_log_product_with_tiny_width() -> None:
    interval = log_overhead_interval((9.0, 9.0), precision=64)
    with localcontext() as context:
        context.prec = 80
        exact_reference = Decimal(9).ln() * 2
    assert interval.lower < exact_reference < interval.upper
    assert interval.width < Decimal("1e-50")
    assert conservative_factor(interval, interval) >= 1.0
