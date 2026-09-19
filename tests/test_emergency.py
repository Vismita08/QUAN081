"""
Unit tests for Emergency Green Corridor routing, green wave override, and automatic signal restoration.
"""

import unittest
import config
from simulation.network import TrafficNetwork
from emergency.corridor import EmergencyCorridor

class TestEmergency(unittest.TestCase):
    def setUp(self):
        config.set_seed()
        self.net = TrafficNetwork()
        self.corridor = EmergencyCorridor(self.net)

    def test_emergency_trigger_and_pathfinding(self):
        path = self.corridor.trigger_emergency('A', 'F')
        self.assertTrue(self.corridor.is_active)
        self.assertEqual(path[0], 'A')
        self.assertEqual(path[-1], 'F')
        self.assertEqual(self.corridor.get_current_ambulance_node(), 'A')

    def test_emergency_rerouting_around_road_closure(self):
        # Close edge (A, B). The ambulance must find alternate route (e.g. A -> D -> E -> F)
        self.net.close_road('A', 'B')
        path = self.corridor.trigger_emergency('A', 'F')
        self.assertNotIn(('A', 'B'), zip(path, path[1:]))
        self.assertEqual(path[0], 'A')
        self.assertEqual(path[1], 'D')
        self.assertEqual(path[-1], 'F')

    def test_green_corridor_override_and_step_progression(self):
        self.corridor.trigger_emergency('A', 'F')
        base_decisions = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'E': 0, 'F': 0}
        override_decisions = self.corridor.apply_emergency_override(base_decisions)

        # Corridor nodes must be overridden to Green (1)
        self.assertEqual(override_decisions['A'], 1)

        # Apply signal to network so ambulance can advance
        self.net.set_signal('A', 1)
        self.corridor.step()

        # Ambulance should have moved to the next node
        next_node = self.corridor.get_current_ambulance_node()
        self.assertNotEqual(next_node, 'A')

    def test_ambulance_hospital_arrival_and_restoration(self):
        self.corridor.trigger_emergency('A', 'F')
        # Traverse entire path by always setting green
        while self.corridor.is_active:
            cur = self.corridor.get_current_ambulance_node()
            self.net.set_signal(cur, 1)
            self.corridor.step()

        self.assertTrue(self.corridor.completed)
        self.assertFalse(self.corridor.is_active)
        # All emergency priorities should be cleared
        for s in self.net.intersections.values():
            self.assertFalse(s.emergency_priority)

if __name__ == '__main__':
    unittest.main()
