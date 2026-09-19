"""
Qiskit QAOA implementation using local AerSimulator.
"""

from typing import Dict, Tuple, Any, List
import numpy as np
from scipy.optimize import minimize
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import SparsePauliOp, Statevector
from qiskit_aer import AerSimulator
import config

class QAOAOptimizerQiskit:
    def __init__(self, reps: int = config.QAOA_REPS, shots: int = config.QAOA_SHOTS):
        self.reps = reps
        self.shots = shots
        self.backend = AerSimulator()

    def build_qaoa_circuit(self, h: Dict[int, float], J: Dict[Tuple[int, int], float], num_qubits: int, gamma: float, beta: float, measure: bool = True) -> QuantumCircuit:
        """
        Explicitly constructs a p=1 QAOA circuit with cost and mixer unitaries:
        |psi> = exp(-i beta H_M) exp(-i gamma H_C) |+>^n
        """
        qc = QuantumCircuit(num_qubits)

        # 1. Initial State: Equal superposition |+>^n
        qc.h(range(num_qubits))

        # 2. Cost Unitary: exp(-i gamma H_C)
        # Linear terms: Rz(2 * gamma * h_i)
        for i, hi in h.items():
            qc.rz(2.0 * gamma * hi, i)

        # Quadratic terms: exp(-i gamma J_ij Z_i Z_j)
        for (i, j), Jij in J.items():
            qc.cx(i, j)
            qc.rz(2.0 * gamma * Jij, j)
            qc.cx(i, j)

        # 3. Mixer Unitary: exp(-i beta H_M) with H_M = sum X_i
        for i in range(num_qubits):
            qc.rx(2.0 * beta, i)

        if measure:
            qc.measure_all()

        return qc

    def optimize(self, h: Dict[int, float], J: Dict[Tuple[int, int], float], offset: float, num_qubits: int) -> Dict[str, Any]:
        """
        Runs variational optimization for QAOA parameters (gamma, beta)
        and samples the ground state on AerSimulator.
        
        Returns a dictionary with best_bitstring, counts, optimal_params,
        circuit metadata, and expected energy.
        """
        # Variational cost evaluation via exact statevector expectation
        pauli_op = SparsePauliOp.from_list(
            [("I" * num_qubits, offset)] +
            [(("I" * (num_qubits - 1 - i)) + "Z" + ("I" * i), hi) for i, hi in h.items()] +
            [(("I" * (num_qubits - 1 - max(i, j))) + "Z" + ("I" * (max(i, j) - min(i, j) - 1)) + "Z" + ("I" * min(i, j)), Jij) for (i, j), Jij in J.items()]
        )

        def cost_eval(params):
            gamma, beta = params
            # Build circuit without measurement to calculate statevector expectation
            circ = self.build_qaoa_circuit(h, J, num_qubits, gamma, beta, measure=False)
            sv = Statevector.from_instruction(circ)
            exp_val = sv.expectation_value(pauli_op).real
            return exp_val

        # Initial parameter guess
        init_params = [0.45, 0.35]
        opt_res = minimize(cost_eval, init_params, method='COBYLA', options={'maxiter': 25})
        opt_gamma, opt_beta = float(opt_res.x[0]), float(opt_res.x[1])
        final_energy = float(opt_res.fun)

        # Build final parameterized circuit with measurements
        final_qc = self.build_qaoa_circuit(h, J, num_qubits, opt_gamma, opt_beta, measure=True)
        transpiled_qc = transpile(final_qc, self.backend)
        job = self.backend.run(transpiled_qc, shots=self.shots)
        counts = job.result().get_counts()

        # Best bitstring is the highest sampled frequency
        best_bitstring = max(counts, key=counts.get)

        circuit_info = {
            'qubits': num_qubits,
            'depth': final_qc.depth(),
            'gate_count': dict(final_qc.count_ops()),
            'circuit_repr': str(final_qc)
        }

        return {
            'best_bitstring': best_bitstring,
            'counts': counts,
            'opt_gamma': round(opt_gamma, 4),
            'opt_beta': round(opt_beta, 4),
            'expected_energy': round(final_energy, 4),
            'circuit_info': circuit_info,
            'framework': 'Qiskit Aer Simulator'
        }
