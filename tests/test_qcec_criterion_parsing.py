from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_e12_representation_placement_regret.py"

spec = importlib.util.spec_from_file_location("e12_qcec_parser_test", RUNNER)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_qcec_equivalence_parser_is_fail_closed() -> None:
    f = module._qcec_criterion_is_equivalent
    assert f("EquivalenceCriterion.equivalent") is True
    assert f("EquivalenceCriterion.equivalent_up_to_global_phase") is True
    assert f("EquivalenceCriterion.not_equivalent") is False
    assert f("not_equivalent") is False
    assert f("probably_equivalent") is False
    assert f("unknown") is False
