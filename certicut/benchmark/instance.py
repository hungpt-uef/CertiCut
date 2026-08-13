"""Immutable synthetic benchmark instance definitions."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from certicut.circuits.benchmarks import make_benchmark_circuit


@dataclass(frozen=True)
class BenchmarkInstance:
    family: str
    num_qubits: int
    seed: int
    track: str = "A_exact_balanced"

    @property
    def qmax(self) -> int:
        return (self.num_qubits + 1) // 2

    @property
    def instance_id(self) -> str:
        return f"synthetic/{self.family}/n{self.num_qubits}/seed{self.seed:03d}"

    def circuit(self):
        return make_benchmark_circuit(self.family, self.num_qubits, self.seed)

    def as_dict(self):
        return {**asdict(self), "instance_id": self.instance_id, "qmax": self.qmax}
