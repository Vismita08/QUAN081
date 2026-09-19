"""
Environmental & Social Welfare Metrics Evaluation.
Calculates vehicle delays, throughput, estimated fuel consumption, estimated CO2 emissions,
and social welfare indices based on simulation models.
"""

from typing import List, Dict, Any, Optional
import pandas as pd
import config

class MetricsEvaluator:
    def __init__(self, mode_name: str = "Controller"):
        self.mode_name = mode_name
        self.history: Dict[str, List[Any]] = {
            'step': [],
            'total_queue': [],
            'avg_wait_time': [],
            'step_throughput': [],
            'cumulative_throughput': [],
            'step_fuel_liters': [],
            'cumulative_fuel_liters': [],
            'step_co2_kg': [],
            'cumulative_co2_kg': [],
            'pedestrian_demand': [],
            'emergency_transit_steps': []
        }
        self.total_switches = 0
        self.prev_decisions: Optional[Dict[str, int]] = None

    def record_step(
        self,
        step: int,
        total_queue: int,
        avg_wait: float,
        throughput: int,
        pedestrian_demand: int = 0,
        current_decisions: Optional[Dict[str, int]] = None,
        emergency_transit_step: int = 0
    ):
        # 1. Track signal switching for stop-and-go penalty
        switches = 0
        if current_decisions and self.prev_decisions:
            for node, bit in current_decisions.items():
                if self.prev_decisions.get(node) != bit:
                    switches += 1
        self.total_switches += switches
        if current_decisions:
            self.prev_decisions = current_decisions.copy()

        # 2. Estimate Fuel Consumption (Liters)
        # Idling in queue + acceleration from stops
        fuel_idle = total_queue * config.FUEL_IDLE_PER_VEHICLE_STEP
        fuel_switch = switches * config.FUEL_SWITCH_PENALTY
        step_fuel = fuel_idle + fuel_switch

        # 3. Estimate CO2 Emissions (kg)
        step_co2 = step_fuel * config.CO2_PER_LITER_FUEL

        # 4. Cumulative aggregations
        prev_cum_thru = self.history['cumulative_throughput'][-1] if self.history['cumulative_throughput'] else 0
        prev_cum_fuel = self.history['cumulative_fuel_liters'][-1] if self.history['cumulative_fuel_liters'] else 0.0
        prev_cum_co2 = self.history['cumulative_co2_kg'][-1] if self.history['cumulative_co2_kg'] else 0.0

        cum_thru = prev_cum_thru + throughput
        cum_fuel = prev_cum_fuel + step_fuel
        cum_co2 = prev_cum_co2 + step_co2

        # 5. Append to history
        self.history['step'].append(step)
        self.history['total_queue'].append(total_queue)
        self.history['avg_wait_time'].append(round(avg_wait, 2))
        self.history['step_throughput'].append(throughput)
        self.history['cumulative_throughput'].append(cum_thru)
        self.history['step_fuel_liters'].append(round(step_fuel, 4))
        self.history['cumulative_fuel_liters'].append(round(cum_fuel, 3))
        self.history['step_co2_kg'].append(round(step_co2, 4))
        self.history['cumulative_co2_kg'].append(round(cum_co2, 3))
        self.history['pedestrian_demand'].append(pedestrian_demand)
        self.history['emergency_transit_steps'].append(emergency_transit_step)

    def get_summary(self) -> Dict[str, Any]:
        """Returns consolidated key performance indicators (KPIs)."""
        if not self.history['step']:
            return {}

        avg_q = sum(self.history['total_queue']) / len(self.history['total_queue'])
        avg_wait = sum(self.history['avg_wait_time']) / len(self.history['avg_wait_time'])
        total_thru = self.history['cumulative_throughput'][-1]
        total_fuel = self.history['cumulative_fuel_liters'][-1]
        total_co2 = self.history['cumulative_co2_kg'][-1]
        avg_ped = sum(self.history['pedestrian_demand']) / len(self.history['pedestrian_demand'])

        # Social Welfare Index (higher is better): Throughput / (Delay + Emissions + Disruption)
        welfare_index = (total_thru * 10.0) / max(1.0, (avg_q * 1.5 + total_co2 * 2.0 + avg_ped * 0.5))

        return {
            'mode': self.mode_name,
            'total_steps': len(self.history['step']),
            'avg_queue': round(avg_q, 1),
            'avg_wait_time': round(avg_wait, 2),
            'total_throughput': total_thru,
            'total_fuel_liters': round(total_fuel, 2),
            'total_co2_kg': round(total_co2, 2),
            'avg_pedestrian_demand': round(avg_ped, 1),
            'social_welfare_index': round(welfare_index, 2)
        }

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.history)

    def reset(self):
        for k in self.history:
            self.history[k].clear()
        self.total_switches = 0
        self.prev_decisions = None
