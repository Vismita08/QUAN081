import numpy as np
from qiskit.circuit.library import QAOAAnsatz
from qiskit.primitives import StatevectorEstimator
from scipy.optimize import minimize
from qiskit.quantum_info import SparsePauliOp
from qiskit_aer import AerSimulator
from qiskit import transpile

import config

class QAOAOptimizer:
    def __init__(self, reps: int = config.QAOA_REPS):
        self.reps = reps
        self.backend = AerSimulator()
        
    def optimize(self, hamiltonian: SparsePauliOp):
        """
        Runs QAOA to find the ground state of the Hamiltonian.
        Returns the most probable bitstring.
        """
        ansatz = QAOAAnsatz(hamiltonian, reps=self.reps)
        estimator = StatevectorEstimator()
        
        def cost_func(params):
            # V2 Estimator takes tuples of (circuit, observable, parameter_values)
            pub = (ansatz, hamiltonian, params)
            job = estimator.run([pub])
            result = job.result()[0]
            # In V2, the expected value is in result.data.evs
            return result.data.evs
            
        initial_point = np.random.rand(ansatz.num_parameters) * 2 * np.pi
        
        res = minimize(cost_func, initial_point, method='COBYLA')
        optimal_params = res.x
        
        ansatz_opt = ansatz.assign_parameters(optimal_params)
        ansatz_opt.measure_all()
        
        qc_transpiled = transpile(ansatz_opt, self.backend)
        job = self.backend.run(qc_transpiled, shots=config.QAOA_SHOTS)
        counts = job.result().get_counts()
        
        best_bitstring = max(counts, key=counts.get)
        
        return best_bitstring, counts
