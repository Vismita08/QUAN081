"""
Unit tests for traffic micro-simulation flow and queue dynamics.
"""

import unittest
import config
from simulation.network import TrafficNetwork
from simulation.traffic import TrafficSimulator

class TestTraffic(unittest.TestCase):
    def setUp(self):
        config.set_seed()
        self.net = TrafficNetwork()
        self.sim = TrafficSimulator(self.net)

    def test_simulation_step_accumulates_queues(self):
        initial_q = self.sim.get_total_queue_length()
        step_res = self.sim.step()
        new_q = self.sim.get_total_queue_length()

        self.assertEqual(step_res['step'], 1)
        self.assertGreater(step_res['step_arrivals'], 0)
        self.assertGreaterEqual(new_q, initial_q)

    def test_green_signal_clears_queue_faster_than_red(self):
        # Give node A green and node B red, both with 15 initial cars
        self.net.get_state('A').queue_length = 15
        self.net.get_state('B').queue_length = 15
        self.net.set_signal('A', 1)
        self.net.set_signal('B', 0)

        # Step simulation
        self.sim.step()

        # Node A should discharge up to 6 vehicles, whereas B discharges at most 1
        q_a = self.net.get_state('A').queue_length
        q_b = self.net.get_state('B').queue_length
        self.assertLess(q_a, q_b)

if __name__ == '__main__':
    unittest.main()
