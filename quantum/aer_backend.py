"""
Local Qiskit Aer backend management.
"""

from typing import Dict, Any
from qiskit_aer import AerSimulator
import config

class AerBackendManager:
    def __init__(self):
        self.simulator = AerSimulator()

    def get_backend_info(self) -> Dict[str, Any]:
        return {
            'name': 'Qiskit Aer Simulator',
            'type': 'Local Quantum Simulator',
            'status': 'ONLINE',
            'num_qubits_supported': 30,
            'is_real_hardware': False,
            'description': 'High-performance C++ based local simulator with zero latency and no queue delay.'
        }
