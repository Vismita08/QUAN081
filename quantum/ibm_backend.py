"""
IBM Quantum Hardware backend manager with automatic Aer fallback.
Never hardcodes credentials; reads securely from environment variables.
"""

import os
from typing import Dict, Any, Optional, Tuple
from qiskit_aer import AerSimulator

class IBMQuantumManager:
    def __init__(self):
        self.service = None
        self.token = os.getenv("IBM_QUANTUM_TOKEN") or os.getenv("QISKIT_IBM_TOKEN")
        self.is_connected = False
        self.selected_backend_name: Optional[str] = None
        self.connection_message = "No IBM Quantum credentials configured (Defaulting to Qiskit Aer)."
        self._initialize_service()

    def _initialize_service(self):
        if not self.token:
            self.connection_message = "IBM_QUANTUM_TOKEN environment variable not set. Running on Qiskit Aer."
            return

        try:
            from qiskit_ibm_runtime import QiskitRuntimeService
            self.service = QiskitRuntimeService(channel="ibm_quantum", token=self.token)
            # Find a suitable backend with at least 6 qubits
            backends = self.service.backends(min_num_qubits=6, operational=True, simulator=False)
            if backends:
                self.selected_backend_name = backends[0].name
                self.is_connected = True
                self.connection_message = f"Connected to IBM Quantum hardware backend: {self.selected_backend_name}"
            else:
                self.connection_message = "Connected to IBM Quantum, but no operational 6+ qubit QPU was available. Falling back to Aer."
        except Exception as e:
            self.is_connected = False
            self.connection_message = f"IBM Quantum connection failed ({type(e).__name__}). Falling back to Qiskit Aer."

    def get_status(self) -> Dict[str, Any]:
        return {
            'is_hardware_available': self.is_connected,
            'active_backend': self.selected_backend_name if self.is_connected else "Qiskit Aer Simulator",
            'is_real_hardware': self.is_connected,
            'status_message': self.connection_message
        }
