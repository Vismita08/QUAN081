"""
Unit tests for QUBO formulation and QUBO-to-Ising mathematical equivalence.
"""

import unittest
import numpy as np
import config
from simulation.network import TrafficNetwork
from optimization.qubo import TrafficQUBO
from optimization.ising import qubo_to_ising, ising_energy

class TestQUBOAndIsing(unittest.TestCase):
    def setUp(self):
        config.set_seed()
        self.net = TrafficNetwork()
        self.qubo = TrafficQUBO(self.net)

    def test_qubo_generation(self):
        # Set some non-zero queues
        self.net.get_state('A').queue_length = 10
        self.net.get_state('B').queue_length = 15
        self.net.get_state('C').pedestrian_demand = 8

        Q, meta = self.qubo.build_qubo_matrix()
        self.assertTrue(len(Q) > 0)
        # All variable indices must be in [0, 5]
        for (i, j) in Q.keys():
            self.assertIn(i, range(6))
            self.assertIn(j, range(6))
            self.assertLessEqual(i, j) # upper triangular

    def test_qubo_to_ising_energy_equivalence(self):
        """
        Crucial mathematical verification:
        For any random bitstring x in {0, 1}^6,
        E_QUBO(x) must equal E_Ising(z) where z_i = 1 - 2*x_i (i.e. x_i = (1 - z_i)/2).
        """
        self.net.get_state('A').queue_length = 12
        self.net.get_state('B').queue_length = 8
        self.net.get_state('C').queue_length = 14
        self.net.get_state('D').pedestrian_demand = 5
        self.net.get_state('E').traffic_density = 9

        Q, _ = self.qubo.build_qubo_matrix(emergency_nodes=['A', 'B'])
        h, J, offset = qubo_to_ising(Q, num_variables=6)

        # Test across 64 all possible binary configurations of 6 variables!
        for b in range(64):
            # Generate binary vector x of length 6
            x = np.array([(b >> k) & 1 for k in range(6)])
            # Corresponding spin vector z: z_i = +1 if x_i == 0, z_i = -1 if x_i == 1
            z = 1.0 - 2.0 * x

            # Compute QUBO cost: sum_{i <= j} Q_ij * x_i * x_j
            qubo_cost = 0.0
            for (i, j), w in Q.items():
                if x[i] == 1 and x[j] == 1:
                    qubo_cost += w

            # Compute Ising energy: offset + sum h_i z_i + sum J_ij z_i z_j
            ising_cost = ising_energy(h, J, offset, z)

            # Check precision tolerance within 1e-5
            self.assertAlmostEqual(
                qubo_cost, ising_cost, places=4,
                msg=f"Discrepancy for bitstring {x}: QUBO={qubo_cost}, Ising={ising_cost}"
            )

    def test_solution_decoding(self):
        decisions = self.qubo.decode_solution("000001") # Little endian: node A (idx 0) is rightmost '1'
        self.assertEqual(decisions['A'], 1)
        self.assertEqual(decisions['B'], 0)
        self.assertEqual(decisions['F'], 0)

if __name__ == '__main__':
    unittest.main()
