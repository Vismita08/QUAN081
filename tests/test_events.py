"""
Unit tests for pedestrian demand simulation and dynamic city events.
"""

import unittest
import config
from simulation.network import TrafficNetwork
from simulation.pedestrians import PedestrianManager
from simulation.events import EventManager

class TestPedestriansAndEvents(unittest.TestCase):
    def setUp(self):
        config.set_seed()
        self.net = TrafficNetwork()
        self.ped_mgr = PedestrianManager(self.net)
        self.event_mgr = EventManager(self.net)

    def test_pedestrian_accumulation_and_clearing(self):
        # Set vehicle green (1) so pedestrians are held waiting at crosswalk
        for node in config.INTERSECTION_IDS:
            self.net.set_signal(node, 1)
        self.ped_mgr.step()
        demand = self.ped_mgr.get_total_pedestrian_demand()
        self.assertGreater(demand, 0)

        # Signal state 0 (pedestrian walk phase) clears pedestrians
        self.net.set_signal('A', 0)
        self.net.get_state('A').pedestrian_demand = 15
        self.ped_mgr.step()
        self.assertLess(self.net.get_state('A').pedestrian_demand, 15)

    def test_sudden_congestion_event(self):
        init_q = self.net.get_state('B').queue_length
        self.event_mgr.trigger_sudden_congestion(['B'], extra_vehicles=15)
        new_q = self.net.get_state('B').queue_length
        self.assertEqual(new_q, init_q + 15)

    def test_accident_event_slashes_effective_capacity(self):
        state_c = self.net.get_state('C')
        orig_cap = state_c.capacity
        self.assertEqual(state_c.effective_capacity, orig_cap)

        self.event_mgr.trigger_accident('C', severity=0.70)
        self.assertEqual(state_c.accident_severity, 0.70)
        self.assertLess(state_c.effective_capacity, orig_cap)

        self.event_mgr.clear_accident('C')
        self.assertEqual(state_c.effective_capacity, orig_cap)

    def test_road_closure_modifies_graph(self):
        self.event_mgr.trigger_road_closure('B', 'C')
        self.assertIn(('B', 'C'), self.net.closed_edges)
        active_g = self.net.get_active_graph()
        self.assertFalse(active_g.has_edge('B', 'C'))

        self.event_mgr.clear_road_closure('B', 'C')
        self.assertNotIn(('B', 'C'), self.net.closed_edges)

if __name__ == '__main__':
    unittest.main()
