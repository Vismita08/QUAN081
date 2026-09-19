"""
State representations for intersections in the road network.
"""

from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class IntersectionState:
    id: str
    name: str = ""
    lat: float = 0.0
    lon: float = 0.0
    traffic_density: int = 0
    queue_length: int = 0
    capacity: int = 30
    signal_state: int = 0         # 1 = Green for primary corridor/flow, 0 = Red / Secondary
    green_duration: int = 0       # Steps current green has been held
    pedestrian_demand: int = 0    # Number of pedestrians waiting to cross
    emergency_priority: bool = False # Whether emergency vehicle needs this intersection
    is_blocked: bool = False      # Road closure flag
    accident_severity: float = 0.0 # 0.0 to 1.0; reduces effective capacity
    
    @property
    def effective_capacity(self) -> int:
        if self.is_blocked:
            return 0
        reduction = int(self.capacity * self.accident_severity)
        return max(1, self.capacity - reduction)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'lat': self.lat,
            'lon': self.lon,
            'traffic_density': self.traffic_density,
            'queue_length': self.queue_length,
            'capacity': self.capacity,
            'effective_capacity': self.effective_capacity,
            'signal_state': self.signal_state,
            'green_duration': self.green_duration,
            'pedestrian_demand': self.pedestrian_demand,
            'emergency_priority': self.emergency_priority,
            'is_blocked': self.is_blocked,
            'accident_severity': self.accident_severity
        }

    def copy(self) -> 'IntersectionState':
        return IntersectionState(
            id=self.id,
            name=self.name,
            lat=self.lat,
            lon=self.lon,
            traffic_density=self.traffic_density,
            queue_length=self.queue_length,
            capacity=self.capacity,
            signal_state=self.signal_state,
            green_duration=self.green_duration,
            pedestrian_demand=self.pedestrian_demand,
            emergency_priority=self.emergency_priority,
            is_blocked=self.is_blocked,
            accident_severity=self.accident_severity
        )
