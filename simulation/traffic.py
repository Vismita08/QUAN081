"""
Microscopic traffic flow simulator modeling vehicle queues, departures, throughput, and delays.
"""

import random
from typing import Dict, Any, Tuple
import config
from .network import TrafficNetwork
from .pedestrians import PedestrianManager

class TrafficSimulator:
    def __init__(self, network: TrafficNetwork, pedestrian_manager: PedestrianManager = None):
        self.network = network
        self.pedestrian_manager = pedestrian_manager or PedestrianManager(network)
        self.time_step = 0
        self.total_vehicles_served = 0
        self.total_wait_time = 0.0

    def step(self) -> Dict[str, Any]:
        """Advances the microscopic traffic simulation by one discrete time step."""
        self.time_step += 1
        step_throughput = 0
        step_arrivals = 0

        # Step 1: Update pedestrian movement and demand
        self.pedestrian_manager.step()

        # Step 2: Vehicle arrivals
        for node_id, state in self.network.intersections.items():
            if state.is_blocked:
                continue

            # Influx of new vehicles
            base_inflow = random.randint(config.BASE_ARRIVAL_RATE_MIN, config.BASE_ARRIVAL_RATE_MAX)
            # Edge nodes like A, D get higher commuter influx
            if node_id in ['A', 'D']:
                base_inflow += 1

            state.traffic_density = min(state.capacity, state.traffic_density + base_inflow)
            state.queue_length = min(state.effective_capacity, state.queue_length + base_inflow)
            step_arrivals += base_inflow

        # Step 3: Vehicle departures based on signal state and downstream capacity
        for node_id, state in self.network.intersections.items():
            if state.is_blocked or state.queue_length <= 0:
                continue

            # Departure capacity based on signal
            if state.signal_state == 1:
                # Green signal: high discharge rate, scaled down if accident present
                discharge_cap = config.GREEN_DISCHARGE_MAX
                if state.accident_severity > 0:
                    discharge_cap = max(1, int(discharge_cap * (1.0 - state.accident_severity)))
                departures = min(state.queue_length, discharge_cap)
            else:
                # Red signal: minimal turning/leakage flow
                departures = min(state.queue_length, config.RED_DISCHARGE_MAX)

            state.queue_length = max(0, state.queue_length - departures)
            state.traffic_density = max(0, state.traffic_density - departures)
            step_throughput += departures

        self.total_vehicles_served += step_throughput

        # Step 4: Aggregate metrics
        total_queue = self.get_total_queue_length()
        avg_queue = total_queue / len(self.network.intersections)
        avg_wait = self.get_average_wait_time()
        self.total_wait_time += total_queue

        # Congestion Index (Ratio of current queue to max capacity)
        max_possible_queue = sum(s.capacity for s in self.network.intersections.values())
        congestion_index = (total_queue / max_possible_queue) * 100.0 if max_possible_queue > 0 else 0.0

        return {
            'step': self.time_step,
            'step_arrivals': step_arrivals,
            'step_throughput': step_throughput,
            'total_queue': total_queue,
            'avg_queue': avg_queue,
            'avg_wait_time': avg_wait,
            'congestion_index': congestion_index,
            'total_served': self.total_vehicles_served
        }

    def get_total_queue_length(self) -> int:
        return sum(s.queue_length for s in self.network.intersections.values())

    def get_average_wait_time(self) -> float:
        """Average waiting delay (seconds/step) experienced per queued vehicle."""
        total_q = self.get_total_queue_length()
        if not self.network.intersections:
            return 0.0
        return float(total_q) / len(self.network.intersections)

    def reset(self):
        self.time_step = 0
        self.total_vehicles_served = 0
        self.total_wait_time = 0.0
        self.network.reset()
