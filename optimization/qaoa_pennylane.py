"""
PennyLane QAOA implementation using the same QUBO/Ising formulation on default.qubit.
Demonstrates quantum framework agnosticism and portability.
"""

from typing import Dict, Tuple, Any, List
import pennylane as qml
from pennylane import numpy as pnp
import numpy as np
import config

class QAOAOptimizerPennyLane:
    def __init__(self, reps: int = config.QAOA_REPS, shots: int = config.QAOA_SHOTS):
        self.reps = reps
        self.shots = shots

    def build_pennylane_hamiltonian(self, h: Dict[int, float], J: Dict[Tuple[int, int], float], offset: float, num_qubits: int):
        """Constructs a qml.Hamiltonian corresponding to the Ising cost."""
        coeffs = []
        obs = []

        if abs(offset) > 1e-7:
            coeffs.append(float(offset))
            obs.append(qml.Identity(0))

        for i, hi in h.items():
            if abs(hi) > 1e-7:
                coeffs.append(float(hi))
                obs.append(qml.PauliZ(i))

        for (i, j), Jij in J.items():
            if abs(Jij) > 1e-7:
                coeffs.append(float(Jij))
                obs.append(qml.PauliZ(i) @ qml.PauliZ(j))

        if not coeffs:
            coeffs = [0.0]
            obs = [qml.Identity(0)]

        return qml.Hamiltonian(coeffs, obs)

    def optimize(self, h: Dict[int, float], J: Dict[Tuple[int, int], float], offset: float, num_qubits: int) -> Dict[str, Any]:
        """
        Variationally tunes QAOA parameters using PennyLane QNode
        and returns sampled bitstrings and telemetry.
        """
        dev = qml.device("default.qubit", wires=num_qubits)

        H_cost = self.build_pennylane_hamiltonian(h, J, offset, num_qubits)

        def qaoa_circuit(params):
            gamma, beta = params[0], params[1]
            # 1. Hadamard initialization
            for w in range(num_qubits):
                qml.Hadamard(wires=w)

            # 2. Cost layer
            for i, hi in h.items():
                qml.RZ(2.0 * gamma * hi, wires=i)

            for (i, j), Jij in J.items():
                qml.CNOT(wires=[i, j])
                qml.RZ(2.0 * gamma * Jij, wires=j)
                qml.CNOT(wires=[i, j])

            # 3. Mixer layer
            for w in range(num_qubits):
                qml.RX(2.0 * beta, wires=w)

        @qml.qnode(dev)
        def cost_qnode(params):
            qaoa_circuit(params)
            return qml.expval(H_cost)

        @qml.qnode(dev, shots=self.shots)
        def sample_qnode(params):
            qaoa_circuit(params)
            return qml.sample()

        # Variational optimization with PennyLane's GradientDescentOptimizer
        params = pnp.array([0.45, 0.35], requires_grad=True)
        opt = qml.GradientDescentOptimizer(stepsize=0.15)

        for _ in range(12):
            params, cost = opt.step_and_cost(cost_qnode, params)

        opt_gamma, opt_beta = float(params[0]), float(params[1])
        final_energy = float(cost_qnode(params))

        # Sample bitstrings
        raw_samples = sample_qnode(params)
        # Convert samples (numpy array of 0s and 1s) to Qiskit-compatible bitstring counts
        # Note: raw_samples shape is (shots, num_qubits) where column 0 is qubit 0.
        # In little-endian format, qubit 0 is the last character.
        counts: Dict[str, int] = {}
        for sample in raw_samples:
            # Reverse order to match little-endian format: [q0, q1, ..., qn-1] -> "qn-1 ... q1 q0"
            bs_str = "".join(str(int(bit)) for bit in reversed(sample))
            counts[bs_str] = counts.get(bs_str, 0) + 1

        best_bitstring = max(counts, key=counts.get)

        circuit_info = {
            'qubits': num_qubits,
            'wires': list(range(num_qubits)),
            'shots': self.shots,
            'hamiltonian_terms': len(H_cost.ops)
        }

        return {
            'best_bitstring': best_bitstring,
            'counts': counts,
            'opt_gamma': round(opt_gamma, 4),
            'opt_beta': round(opt_beta, 4),
            'expected_energy': round(final_energy, 4),
            'circuit_info': circuit_info,
            'framework': 'PennyLane (default.qubit)'
        }
