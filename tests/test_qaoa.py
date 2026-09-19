"""
Unit tests for Qiskit and PennyLane QAOA execution, circuit properties, and parameter optimization.
"""

import unittest
import config
from simulation.network import TrafficNetwork
from optimization.qubo import TrafficQUBO
from optimization.ising import qubo_to_ising
from optimization.qaoa_qiskit import QAOAOptimizerQiskit
from optimization.qaoa_pennylane import QAOAOptimizerPennyLane

class TestQAOA(unittest.TestCase):
    def setUp(self):
        config.set_seed()
        self.net = TrafficNetwork()
        self.qubo = TrafficQUBO(self.net)

        # Set up a clear priority at node A and B
        self.net.get_state('A').queue_length = 20
        self.net.get_state('B').queue_length = 15
        self.net.get_state('C').queue_length = 2

        Q, _ = self.qubo.build_qubo_matrix()
        self.h, self.J, self.offset = qubo_to_ising(Q, num_variables=6)

    def test_qiskit_qaoa(self):
        optimizer = QAOAOptimizerQiskit(reps=1, shots=512)
        res = optimizer.optimize(self.h, self.J, self.offset, num_qubits=6)

        self.assertIn('best_bitstring', res)
        self.assertEqual(len(res['best_bitstring']), 6)
        self.assertIn('counts', res)
        self.assertGreater(len(res['counts']), 0)
        self.assertEqual(res['circuit_info']['qubits'], 6)
        self.assertIn('opt_gamma', res)
        self.assertIn('opt_beta', res)

    def test_pennylane_qaoa(self):
        optimizer = QAOAOptimizerPennyLane(reps=1, shots=512)
        res = optimizer.optimize(self.h, self.J, self.offset, num_qubits=6)

        self.assertIn('best_bitstring', res)
        self.assertEqual(len(res['best_bitstring']), 6)
        self.assertIn('counts', res)
        self.assertGreater(len(res['counts']), 0)
        self.assertEqual(res['circuit_info']['qubits'], 6)

if __name__ == '__main__':
    unittest.main()
