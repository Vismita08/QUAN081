"""
Classical traffic control baselines:
1. FixedTimeController (standard time-cyclical alternating control)
2. RuleBasedAdaptiveController (greedy queue & pedestrian heuristic)
"""

from typing import Dict, List, Optional
from simulation.network import TrafficNetwork
import config

class FixedTimeController:
    """Rigid cyclical fixed-time controller that ignores real-time traffic changes."""
    def __init__(self, network: TrafficNetwork, cycle_steps: int = 5):
        self.network = network
        self.cycle_steps = cycle_steps
        self.step_counter = 0

    def optimize(self, emergency_nodes: Optional[List[str]] = None) -> Dict[str, int]:
        self.step_counter += 1
        phase = (self.step_counter // self.cycle_steps) % 2

        set_1 = {'A', 'C', 'E'}
        set_2 = {'B', 'D', 'F'}

        decisions = {}
        for node in config.INTERSECTION_IDS:
            if phase == 0:
                decisions[node] = 1 if node in set_1 else 0
            else:
                decisions[node] = 1 if node in set_2 else 0

        # Note: Fixed-time controllers traditionally do not adapt, but may have preemption if triggered
        return decisions

class RuleBasedAdaptiveController:
    """
    Classical rule-based adaptive controller that greedily prioritizes
    intersections with the largest queue while managing conflicts.
    """
    def __init__(self, network: TrafficNetwork):
        self.network = network

    def optimize(self, emergency_nodes: Optional[List[str]] = None) -> Dict[str, int]:
        emg_set = set(emergency_nodes or [])
        decisions: Dict[str, int] = {}

        # Compute urgency score for each intersection
        scores: Dict[str, float] = {}
        for node in config.INTERSECTION_IDS:
            state = self.network.get_state(node)
            is_emg = (node in emg_set) or state.emergency_priority
            # Urgency increases with queue and density, decreases if pedestrians desperately need to cross
            urgency = (state.queue_length * 1.5) + (state.traffic_density * 0.8) - (state.pedestrian_demand * 1.2)
            if is_emg:
                urgency += 100.0
            scores[node] = urgency

        # Greedily activate green for high urgency, but avoid simultaneous greens on direct high-traffic conflicts
        for node in config.INTERSECTION_IDS:
            # If emergency, always grant green
            if (node in emg_set) or self.network.get_state(node).emergency_priority:
                decisions[node] = 1
            elif scores[node] >= 6.0:
                # Moderate threshold for green
                decisions[node] = 1
            else:
                decisions[node] = 0

        return decisions
