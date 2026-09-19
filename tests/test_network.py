"""
Unit tests for road network topology and graph integrity.
"""

import unittest
import networkx as nx
import config
from simulation.network import TrafficNetwork

class TestNetwork(unittest.TestCase):
    def setUp(self):
        config.set_seed()
        self.net = TrafficNetwork()

    def test_node_count_and_coordinates(self):
        self.assertEqual(len(self.net.graph.nodes), 6)
        self.assertEqual(len(self.net.intersections), 6)
        for node_id in config.INTERSECTION_IDS:
            state = self.net.get_state(node_id)
            self.assertIn(node_id, self.net.graph.nodes)
            self.assertGreater(state.capacity, 0)
            self.assertNotEqual(state.lat, 0.0)
            self.assertNotEqual(state.lon, 0.0)

    def test_connectivity(self):
        # Graph must be fully connected
        self.assertTrue(nx.is_connected(self.net.graph))

    def test_road_closure_and_reopening(self):
        self.assertFalse(self.net.is_road_closed('B', 'C'))
        self.net.close_road('B', 'C')
        self.assertTrue(self.net.is_road_closed('B', 'C'))
        self.assertTrue(self.net.is_road_closed('C', 'B')) # bidirectional

        # Active graph should omit the closed road
        active_g = self.net.get_active_graph()
        self.assertFalse(active_g.has_edge('B', 'C'))

        self.net.reopen_road('B', 'C')
        self.assertFalse(self.net.is_road_closed('B', 'C'))

    def test_signal_assignment(self):
        self.net.set_signal('A', 1)
        self.assertEqual(self.net.get_state('A').signal_state, 1)
        self.assertEqual(self.net.get_state('A').green_duration, 1)

        # Holding green increments duration
        self.net.set_signal('A', 1)
        self.assertEqual(self.net.get_state('A').green_duration, 2)

        # Switching to red resets duration
        self.net.set_signal('A', 0)
        self.assertEqual(self.net.get_state('A').signal_state, 0)
        self.assertEqual(self.net.get_state('A').green_duration, 0)

if __name__ == '__main__':
    unittest.main()
