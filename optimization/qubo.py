"""
Quadratic Unconstrained Binary Optimization (QUBO) formulation for adaptive urban traffic.
"""

from typing import Dict, Tuple, List, Any
import numpy as np
import config
from simulation.network import TrafficNetwork

class TrafficQUBO:
    def __init__(self, network: TrafficNetwork, weights: Dict[str, float] = None):
        self.network = network
        self.weights = weights or config.QUBO_WEIGHTS.copy()
        self.nodes = config.INTERSECTION_IDS
        self.num_nodes = len(self.nodes)
        self.node_to_idx = {node: i for i, node in enumerate(self.nodes)}

    def build_qubo_matrix(self, emergency_nodes: List[str] = None) -> Tuple[Dict[Tuple[int, int], float], Dict[str, Any]]:
        """
        Constructs the upper-triangular QUBO matrix Q such that:
        Cost(x) = sum_{i <= j} Q_{ij} x_i x_j
        where x_i in {0, 1}.
        
        Returns:
            Q_matrix: dict mapping (i, j) -> float (with i <= j)
            metadata: dictionary describing terms and coefficients
        """
        emg_set = set(emergency_nodes or [])
        Q: Dict[Tuple[int, int], float] = {}
        metadata = {'linear_terms': {}, 'quadratic_terms': {}, 'objective_breakdown': {}}

        w_wait = self.weights.get('w_wait', 1.2)
        w_queue = self.weights.get('w_queue', 1.5)
        w_density = self.weights.get('w_density', 1.0)
        w_ped = self.weights.get('w_ped', 1.4)
        w_emg = self.weights.get('w_emg', 12.0)
        w_thru = self.weights.get('w_thru', 0.8)
        w_switch = self.weights.get('w_switch', 0.4)
        p_conflict = self.weights.get('p_conflict', 4.0)

        # 1. Linear terms Q_{ii}
        for i, node in enumerate(self.nodes):
            state = self.network.get_state(node)
            q_len = float(state.queue_length)
            density = float(state.traffic_density)
            capacity = float(state.effective_capacity)
            ped_demand = float(state.pedestrian_demand)
            prev_signal = state.signal_state
            is_emg = (node in emg_set) or state.emergency_priority

            # Objective components:
            # - Reward clearing vehicle queue and density (negative cost)
            queue_term = - (w_wait * 0.5 + w_queue) * q_len
            density_term = - w_density * density
            thru_term = - w_thru * (capacity / 5.0)

            # - High pedestrian demand penalizes vehicle green (favors pedestrian cross phase x_i = 0)
            ped_term = + w_ped * ped_demand

            # - Emergency corridor priority: strong negative cost for green
            emg_term = - (w_emg * 35.0) if is_emg else 0.0

            # - Fuel/Emissions switch penalty: penalize abrupt phase change
            switch_term = + (w_switch * 6.0) if prev_signal == 0 else - (w_switch * 4.0)

            total_linear = queue_term + density_term + thru_term + ped_term + emg_term + switch_term
            Q[(i, i)] = total_linear

            metadata['linear_terms'][node] = {
                'total_linear': round(total_linear, 3),
                'queue_term': round(queue_term, 3),
                'ped_term': round(ped_term, 3),
                'emg_term': round(emg_term, 3),
                'switch_term': round(switch_term, 3)
            }

        # 2. Quadratic coupling terms Q_{ij} for (i, j) in Edges (i < j)
        active_graph = self.network.get_active_graph()
        for u, v in active_graph.edges:
            i = self.node_to_idx[u]
            j = self.node_to_idx[v]
            if i > j:
                i, j = j, i

            # If both nodes are part of emergency corridor, reward coordinated green wave
            if u in emg_set and v in emg_set:
                coupling = - (p_conflict * 2.5) # Green wave reward
                relation = "Emergency Green Wave Coordination"
            else:
                # Standard anti-conflict penalty to prevent simultaneous uncoordinated saturation
                coupling = p_conflict
                relation = "Anti-Congestion Coordination"

            Q[(i, j)] = Q.get((i, j), 0.0) + coupling
            metadata['quadratic_terms'][f"{u}-{v}"] = {
                'coupling': round(coupling, 3),
                'relation': relation
            }

        return Q, metadata

    def decode_solution(self, bitstring: str) -> Dict[str, int]:
        """
        Decodes measured quantum bitstring into intersection signal states.
        Bitstring is formatted standard MSB-first or LSB-first.
        We map index i to self.nodes[i].
        """
        decisions = {}
        # In Qiskit, standard bitstring has bit 0 at the right (little endian):
        # i.e., bitstring[-(i+1)] corresponds to qubit i.
        # Handle both standard string formats safely:
        n = len(self.nodes)
        clean_bs = bitstring.replace(' ', '')
        if len(clean_bs) != n:
            raise ValueError(f"Bitstring length {len(clean_bs)} does not match number of nodes {n}")

        for i, node in enumerate(self.nodes):
            # Qiskit measurement string is little-endian: qubit 0 is clean_bs[-1]
            bit = int(clean_bs[n - 1 - i])
            decisions[node] = bit
        return decisions

    def evaluate_cost(self, Q: Dict[Tuple[int, int], float], bitstring: str) -> float:
        """Calculates the classical QUBO cost for a given bitstring."""
        decisions = self.decode_solution(bitstring)
        x = [decisions[node] for node in self.nodes]
        cost = 0.0
        for (i, j), weight in Q.items():
            if x[i] == 1 and x[j] == 1:
                cost += weight
        return cost
