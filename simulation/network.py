"""
Road network graph and topology using NetworkX.
"""

import networkx as nx
from typing import Dict, List, Tuple, Optional
import config
from .state import IntersectionState

class TrafficNetwork:
    def __init__(self):
        self.graph = nx.Graph()
        self.intersections: Dict[str, IntersectionState] = {}
        self.closed_edges: List[Tuple[str, str]] = []
        self.build_network()

    def build_network(self):
        self.graph.clear()
        self.intersections.clear()
        self.closed_edges.clear()

        # Add nodes with coordinates and metadata
        for node_id in config.INTERSECTION_IDS:
            meta = config.INTERSECTION_METADATA[node_id]
            self.graph.add_node(
                node_id,
                name=meta['name'],
                lat=meta['lat'],
                lon=meta['lon'],
                is_origin=meta.get('is_origin', False),
                is_hospital=meta.get('is_hospital', False)
            )
            self.intersections[node_id] = IntersectionState(
                id=node_id,
                name=meta['name'],
                lat=meta['lat'],
                lon=meta['lon'],
                traffic_density=0,
                queue_length=0,
                capacity=config.MAX_QUEUE_CAPACITY,
                signal_state=0
            )

        # Add edges with physical road attributes
        for u, v, attrs in config.ROAD_EDGES:
            self.graph.add_edge(u, v, **attrs)

    def get_state(self, intersection_id: str) -> IntersectionState:
        return self.intersections[intersection_id]

    def set_signal(self, intersection_id: str, state: int):
        cur = self.intersections[intersection_id]
        if cur.signal_state == state and state == 1:
            cur.green_duration += 1
        elif state == 1:
            cur.signal_state = 1
            cur.green_duration = 1
        else:
            cur.signal_state = 0
            cur.green_duration = 0

    def close_road(self, u: str, v: str):
        edge_key = (min(u, v), max(u, v))
        if edge_key not in self.closed_edges:
            self.closed_edges.append(edge_key)

    def reopen_road(self, u: str, v: str):
        edge_key = (min(u, v), max(u, v))
        if edge_key in self.closed_edges:
            self.closed_edges.remove(edge_key)

    def is_road_closed(self, u: str, v: str) -> bool:
        return (min(u, v), max(u, v)) in self.closed_edges

    def get_active_graph(self) -> nx.Graph:
        """Returns a view of the graph excluding physically closed roads."""
        active_g = self.graph.copy()
        for u, v in self.closed_edges:
            if active_g.has_edge(u, v):
                active_g.remove_edge(u, v)
        return active_g

    def reset(self):
        self.build_network()
