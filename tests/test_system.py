"""
System-level verification tests.
"""

import unittest
import config
from simulation.network import TrafficNetwork
from optimization.qubo import TrafficQUBO
from optimization.ising import qubo_to_ising
from optimization.qaoa_qiskit import QAOAOptimizerQiskit

class TestSystem(unittest.TestCase):
    def test_network_init(self):
        config.set_seed()
        net = TrafficNetwork()
        self.assertEqual(len(net.graph.nodes), 6)

    def test_qubo_hamiltonian(self):
        config.set_seed()
        net = TrafficNetwork()
        qubo = TrafficQUBO(net)
        Q, _ = qubo.build_qubo_matrix()
        h, J, offset = qubo_to_ising(Q, num_variables=6)
        self.assertEqual(len(h) + len(J) > 0, True)

    def test_qaoa_optimizer(self):
        config.set_seed()
        net = TrafficNetwork()
        qubo = TrafficQUBO(net)
        Q, _ = qubo.build_qubo_matrix()
        h, J, offset = qubo_to_ising(Q, num_variables=6)
        qaoa = QAOAOptimizerQiskit(reps=1, shots=256)
        res = qaoa.optimize(h, J, offset, num_qubits=6)
        self.assertEqual(len(res['best_bitstring']), 6)

if __name__ == '__main__':
    unittest.main()
