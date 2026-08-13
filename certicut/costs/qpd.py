"""Qiskit 0.10 compatible independent QPD gate-cost adapter."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite, log
from typing import Any

from qiskit.circuit import Instruction
from qiskit.circuit.parameterexpression import ParameterExpression
from qiskit_addon_cutting.qpd import QPDBasis


class QPDCostError(ValueError):
    """Base QPD cost lookup error."""


class QPDCostUnboundParameter(QPDCostError):
    """A parameterized operation cannot be assigned a numeric overhead."""


class QPDCostUnsupported(QPDCostError):
    """Qiskit could not produce an independent QPD decomposition."""


@dataclass(frozen=True)
class QPDCost:
    gate_name: str
    gate_params: tuple[float, ...]
    overhead: float
    log_cost: float
    source: str = "qiskit_qpd_0.10.0"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def qpd_cost(operation: Instruction) -> QPDCost:
    """Return Qiskit-provided independent QPD sampling overhead for a numeric 2q operation."""
    if operation.num_qubits != 2:
        raise QPDCostUnsupported(f"QPD V1 supports only two-qubit operations, got '{operation.name}'")
    if any(isinstance(parameter, ParameterExpression) and parameter.parameters for parameter in operation.params):
        raise QPDCostUnboundParameter(f"operation '{operation.name}' has unbound parameters")
    try:
        params = tuple(float(parameter) for parameter in operation.params)
        overhead = float(QPDBasis.from_instruction(operation).overhead)
    except Exception as error:
        raise QPDCostUnsupported(f"no Qiskit QPD cost for '{operation.name}': {error}") from error
    if not isfinite(overhead) or overhead < 1:
        raise QPDCostUnsupported(f"invalid QPD overhead {overhead} for '{operation.name}'")
    return QPDCost(operation.name, params, overhead, log(overhead))
