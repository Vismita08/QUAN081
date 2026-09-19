"""
Emergency Green Corridor Management.
Coordinates ambulance routing, signal preemption, green wave progression, and signal restoration.
"""

from typing import List, Dict, Optional, Any
import networkx as nx
from simulation.network import TrafficNetwork
import config

class EmergencyCorridor:
    def __init__(self, network: TrafficNetwork):
        self.network = network
        self.origin_node = 'A'
        self.hospital_node = 'F'
        self.ambulance_path: List[str] = []
        self.current_step_idx: int = -1
        self.is_active: bool = False
        self.travel_time_steps: int = 0
        self.completed: bool = False
        self.disruption_delay_added: float = 0.0

    def trigger_emergency(self, origin: str = 'A', destination: str = 'F') -> List[str]:
        """
        Activates emergency mode, calculates shortest path using currently open roads,
        and marks nodes for green wave priority.
        """
        self.origin_node = origin
        self.hospital_node = destination
        self.travel_time_steps = 0
        self.completed = False
        self.disruption_delay_added = 0.0

        # Calculate route using only non-closed roads
        active_g = self.network.get_active_graph()
        try:
            self.ambulance_path = nx.shortest_path(active_g, source=origin, target=destination, weight='distance_m')
            self.current_step_idx = 0
            self.is_active = True
            self._update_node_priorities()
            return self.ambulance_path
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            self.ambulance_path = []
            self.is_active = False
            return []

    def _update_node_priorities(self):
        """Sets emergency priority flags on network nodes."""
        for node_id, state in self.network.intersections.items():
            state.emergency_priority = False

        if self.is_active and self.current_step_idx < len(self.ambulance_path):
            # Prioritize current node and the next downstream node in the corridor
            current_node = self.ambulance_path[self.current_step_idx]
            self.network.get_state(current_node).emergency_priority = True

            if self.current_step_idx + 1 < len(self.ambulance_path):
                next_node = self.ambulance_path[self.current_step_idx + 1]
                self.network.get_state(next_node).emergency_priority = True

    def get_corridor_nodes(self) -> List[str]:
        """Returns all nodes currently on the designated emergency path."""
        return list(self.ambulance_path) if self.is_active else []

    def get_current_ambulance_node(self) -> Optional[str]:
        """Returns the current intersection where the ambulance is located."""
        if self.is_active and 0 <= self.current_step_idx < len(self.ambulance_path):
            return self.ambulance_path[self.current_step_idx]
        return None

    def apply_emergency_override(self, decisions: Dict[str, int]) -> Dict[str, int]:
        """
        Ensures green light along the emergency green corridor.
        Other nodes maintain optimized signals.
        """
        if not self.is_active:
            return decisions

        updated_decisions = decisions.copy()
        current_node = self.get_current_ambulance_node()
        if current_node:
            updated_decisions[current_node] = 1 # Force green

            # If next node exists, also hold green to clear oncoming queues ahead of ambulance
            if self.current_step_idx + 1 < len(self.ambulance_path):
                next_node = self.ambulance_path[self.current_step_idx + 1]
                updated_decisions[next_node] = 1

        return updated_decisions

    def step(self):
        """
        Advances the ambulance along the corridor if green light is established.
        Upon reaching hospital, automatically deactivates and restores normal operation.
        """
        if not self.is_active:
            return

        self.travel_time_steps += 1
        current_node = self.get_current_ambulance_node()

        if current_node:
            state = self.network.get_state(current_node)
            # Normal cross-traffic queue delay added during override
            self.disruption_delay_added += 2.5

            # If signal is green, ambulance moves forward
            if state.signal_state == 1:
                self.current_step_idx += 1
                if self.current_step_idx >= len(self.ambulance_path):
                    # Arrived at hospital!
                    self.is_active = False
                    self.completed = True
                    self._clear_all_priorities()
                else:
                    self._update_node_priorities()

    def _clear_all_priorities(self):
        """Restores normal traffic signal operation across all intersections."""
        for state in self.network.intersections.values():
            state.emergency_priority = False

    def reset(self):
        self.is_active = False
        self.completed = False
        self.current_step_idx = -1
        self.ambulance_path = []
        self.travel_time_steps = 0
        self.disruption_delay_added = 0.0
        self._clear_all_priorities()

    def get_status(self) -> Dict[str, Any]:
        return {
            'is_active': self.is_active,
            'completed': self.completed,
            'current_location': self.get_current_ambulance_node(),
            'destination': self.hospital_node,
            'route': self.ambulance_path,
            'progress_step': self.current_step_idx + 1 if self.is_active else (len(self.ambulance_path) if self.completed else 0),
            'total_route_steps': len(self.ambulance_path),
            'travel_time_steps': self.travel_time_steps,
            'disruption_delay': round(self.disruption_delay_added, 1)
        }
