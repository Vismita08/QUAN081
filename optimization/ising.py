"""
QUBO to Ising Hamiltonian transformation:
x_i in {0, 1}  <-->  Z_i in {+1, -1} via  x_i = (1 - Z_i) / 2
"""

from typing import Dict, Tuple, Any
from qiskit.quantum_info import SparsePauliOp
import numpy as np

def qubo_to_ising(qubo_matrix: Dict[Tuple[int, int], float], num_variables: int) -> Tuple[Dict[int, float], Dict[Tuple[int, int], float], float]:
    """
    Transforms upper-triangular QUBO Q into Ising Hamiltonian parameters:
    H = Offset + sum_i h_i * Z_i + sum_{i < j} J_{ij} * Z_i * Z_j
    
    Returns:
        h: dictionary mapping qubit index i -> local magnetic field h_i
        J: dictionary mapping (i, j) -> two-body coupling J_{ij}
        offset: constant scalar energy shift
    """
    h: Dict[int, float] = {i: 0.0 for i in range(num_variables)}
    J: Dict[Tuple[int, int], float] = {}
    offset: float = 0.0

    for (i, j), weight in qubo_matrix.items():
        if i == j:
            # Q_ii * x_i = Q_ii * (1 - Z_i)/2 = Q_ii/2 - (Q_ii/2) * Z_i
            offset += weight / 2.0
            h[i] -= weight / 2.0
        else:
            if i > j:
                i, j = j, i
            # Q_ij * x_i * x_j = (Q_ij/4) * (1 - Z_i - Z_j + Z_i * Z_j)
            offset += weight / 4.0
            h[i] -= weight / 4.0
            h[j] -= weight / 4.0
            J[(i, j)] = J.get((i, j), 0.0) + (weight / 4.0)

    # Filter near-zero values
    h_filtered = {k: round(v, 6) for k, v in h.items() if abs(v) > 1e-7}
    J_filtered = {k: round(v, 6) for k, v in J.items() if abs(v) > 1e-7}
    offset = round(offset, 6)

    return h_filtered, J_filtered, offset

def to_qiskit_pauli_op(h: Dict[int, float], J: Dict[Tuple[int, int], float], offset: float, num_qubits: int) -> SparsePauliOp:
    """
    Constructs a Qiskit SparsePauliOp representing H = offset*I + sum h_i Z_i + sum J_ij Z_i Z_j.
    Note: Qiskit uses little-endian qubit ordering (qubit 0 is at string index num_qubits - 1).
    """
    pauli_list = []
    coeffs = []

    # Offset Identity
    if abs(offset) > 1e-7:
        pauli_list.append("I" * num_qubits)
        coeffs.append(offset)

    # 1-body terms (Z_i)
    for i, hi in h.items():
        if abs(hi) > 1e-7:
            p = ['I'] * num_qubits
            p[num_qubits - 1 - i] = 'Z'
            pauli_list.append("".join(p))
            coeffs.append(hi)

    # 2-body terms (Z_i Z_j)
    for (i, j), Jij in J.items():
        if abs(Jij) > 1e-7:
            p = ['I'] * num_qubits
            p[num_qubits - 1 - i] = 'Z'
            p[num_qubits - 1 - j] = 'Z'
            pauli_list.append("".join(p))
            coeffs.append(Jij)

    if not pauli_list:
        return SparsePauliOp(["I" * num_qubits], [0.0])

    return SparsePauliOp(pauli_list, coeffs).simplify()

def ising_energy(h: Dict[int, float], J: Dict[Tuple[int, int], float], offset: float, z: np.ndarray) -> float:
    """Computes classical Ising energy for spin state z with entries in {+1, -1}."""
    energy = offset
    for i, hi in h.items():
        energy += hi * z[i]
    for (i, j), Jij in J.items():
        energy += Jij * z[i] * z[j]
    return energy
