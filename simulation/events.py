"""
Dynamic traffic event simulation (congestion spikes, accidents, road closures).
"""

from typing import List, Dict, Tuple, Optional, Any
from .network import TrafficNetwork

class EventManager:
    def __init__(self, network: TrafficNetwork):
        self.network = network
        self.active_congestion: List[str] = []
        self.active_accidents: Dict[str, float] = {} # node -> severity
        self.active_closures: List[Tuple[str, str]] = []

    def trigger_sudden_congestion(self, nodes: Optional[List[str]] = None, extra_vehicles: int = 15) -> List[str]:
        """Injects a sudden traffic backlog at designated intersections."""
        target_nodes = nodes or ['B', 'E']
        for node in target_nodes:
            if node in self.network.intersections:
                state = self.network.get_state(node)
                state.queue_length = min(state.capacity, state.queue_length + extra_vehicles)
                state.traffic_density = min(state.capacity, state.traffic_density + extra_vehicles)
                if node not in self.active_congestion:
                    self.active_congestion.append(node)
        return target_nodes

    def trigger_accident(self, node: str = 'B', severity: float = 0.70) -> str:
        """Simulates a vehicular collision reducing road capacity and creating queue spillover."""
        if node in self.network.intersections:
            state = self.network.get_state(node)
            state.accident_severity = severity
            # Add sudden stalled vehicles
            state.queue_length = min(state.capacity, state.queue_length + 10)
            self.active_accidents[node] = severity
            return node
        return ""

    def trigger_road_closure(self, u: str = 'B', v: str = 'C') -> Tuple[str, str]:
        """Blocks a road segment completely, forcing traffic rerouting."""
        self.network.close_road(u, v)
        edge_key = (min(u, v), max(u, v))
        if edge_key not in self.active_closures:
            self.active_closures.append(edge_key)
        # Blocked road pushes queue onto upstream node
        state_u = self.network.get_state(u)
        state_u.queue_length = min(state_u.capacity, state_u.queue_length + 8)
        return edge_key

    def clear_accident(self, node: str):
        if node in self.network.intersections:
            self.network.get_state(node).accident_severity = 0.0
        if node in self.active_accidents:
            del self.active_accidents[node]

    def clear_road_closure(self, u: str, v: str):
        self.network.reopen_road(u, v)
        edge_key = (min(u, v), max(u, v))
        if edge_key in self.active_closures:
            self.active_closures.remove(edge_key)

    def clear_all_events(self):
        for node in list(self.active_accidents.keys()):
            self.clear_accident(node)
        for u, v in list(self.active_closures):
            self.clear_road_closure(u, v)
        self.active_congestion.clear()

    def get_summary(self) -> Dict[str, Any]:
        return {
            'congestion': list(self.active_congestion),
            'accidents': dict(self.active_accidents),
            'closures': [f"{u}-{v}" for u, v in self.active_closures]
        }
