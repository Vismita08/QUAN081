"""
Pedestrian demand simulation and crossing behavior.
"""

import random
from typing import Dict
import config
from .network import TrafficNetwork

class PedestrianManager:
    def __init__(self, network: TrafficNetwork):
        self.network = network

    def step(self):
        """Simulates pedestrian arrivals and departures based on signal phases."""
        for node_id, state in self.network.intersections.items():
            # Pedestrian arrivals: tourist/commuter hotspots like C (Trafalgar) have higher arrival
            hotspot_boost = 1 if node_id in ['A', 'C', 'E'] else 0
            new_pedestrians = random.randint(0, config.PEDESTRIAN_ARRIVAL_MAX) + hotspot_boost
            state.pedestrian_demand = min(config.MAX_PEDESTRIAN_QUEUE, state.pedestrian_demand + new_pedestrians)

            # Pedestrian crossing discharge:
            # When signal_state == 0 (Cross phase / pedestrian walk window active), pedestrians cross safely
            if state.signal_state == 0:
                cleared = min(state.pedestrian_demand, config.PEDESTRIAN_CROSSING_CLEAR_RATE)
                state.pedestrian_demand -= cleared
            else:
                # During high-speed green (signal_state == 1), only minimal or zero pedestrians cross
                state.pedestrian_demand = max(0, state.pedestrian_demand - 1)

    def add_demand(self, node_id: str, count: int):
        if node_id in self.network.intersections:
            state = self.network.intersections[node_id]
            state.pedestrian_demand = min(config.MAX_PEDESTRIAN_QUEUE, state.pedestrian_demand + count)

    def get_total_pedestrian_demand(self) -> int:
        return sum(s.pedestrian_demand for s in self.network.intersections.values())
