"""
Configuration parameters for Quantum-Enhanced Adaptive Urban Traffic Optimization.
"""

import random
import numpy as np

# Network Configuration
NUM_INTERSECTIONS = 6
INTERSECTION_IDS = ['A', 'B', 'C', 'D', 'E', 'F']

INTERSECTION_METADATA = {
    'A': {'name': 'Parliament Square', 'lat': 51.5005, 'lon': -0.1268, 'is_origin': True},
    'B': {'name': 'Whitehall / Downing St', 'lat': 51.5038, 'lon': -0.1263, 'is_origin': False},
    'C': {'name': 'Trafalgar Square', 'lat': 51.5080, 'lon': -0.1281, 'is_origin': False},
    'D': {'name': 'Westminster Bridge Rd', 'lat': 51.5008, 'lon': -0.1205, 'is_origin': False},
    'E': {'name': 'Embankment Station', 'lat': 51.5068, 'lon': -0.1225, 'is_origin': False},
    'F': {'name': 'St Thomas Hospital Plaza', 'lat': 51.5078, 'lon': -0.1175, 'is_hospital': True}
}

# 2x3 Connected Grid Edges
ROAD_EDGES = [
    ('A', 'B', {'distance_m': 370, 'capacity': 30, 'lanes': 2}),
    ('B', 'C', {'distance_m': 460, 'capacity': 30, 'lanes': 2}),
    ('D', 'E', {'distance_m': 660, 'capacity': 35, 'lanes': 2}),
    ('E', 'F', {'distance_m': 380, 'capacity': 35, 'lanes': 2}),
    ('A', 'D', {'distance_m': 430, 'capacity': 25, 'lanes': 2}),
    ('B', 'E', {'distance_m': 440, 'capacity': 25, 'lanes': 2}),
    ('C', 'F', {'distance_m': 450, 'capacity': 25, 'lanes': 2})
]

# Traffic Dynamics Config
MAX_QUEUE_CAPACITY = 35
BASE_ARRIVAL_RATE_MIN = 1
BASE_ARRIVAL_RATE_MAX = 4
GREEN_DISCHARGE_MAX = 6
RED_DISCHARGE_MAX = 1

# Pedestrian Demand Parameters
PEDESTRIAN_ARRIVAL_MAX = 4
MAX_PEDESTRIAN_QUEUE = 25
PEDESTRIAN_CROSSING_CLEAR_RATE = 8

# Environmental & Fuel Parameters
# Idle fuel consumption rate: ~0.012 L per vehicle per step (~0.6 gal/hr converted)
FUEL_IDLE_PER_VEHICLE_STEP = 0.012
# EPA standard: 2.31 kg CO2 per liter gasoline
CO2_PER_LITER_FUEL = 2.31
# Stop-and-go acceleration penalty in liters
FUEL_SWITCH_PENALTY = 0.005

# QUBO Multi-Objective Default Weights (Social Welfare balancing)
QUBO_WEIGHTS = {
    'w_wait': 1.2,          # Minimize vehicle delay
    'w_queue': 1.5,         # Minimize queue backlog
    'w_density': 1.0,       # Relieve dense road corridors
    'w_ped': 1.4,           # Pedestrian safety & crossing accommodation
    'w_emg': 12.0,          # Massive priority for emergency green corridor
    'w_thru': 0.8,          # Reward high capacity throughput
    'w_switch': 0.4,        # Penalize stop-and-go phase flickering
    'p_conflict': 4.0       # Penalty for uncoordinated adjacent green lights causing spillover
}

# Quantum Configuration
QAOA_REPS = 1
QAOA_SHOTS = 1024
DEFAULT_QUANTUM_BACKEND = 'AerSimulator'

# Random Seed for Reproducibility
SEED = 42

def set_seed(seed=SEED):
    random.seed(seed)
    np.random.seed(seed)
