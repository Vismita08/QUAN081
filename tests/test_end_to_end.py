"""
End-to-end integration test verifying the complete data pipeline:
Traffic State -> QUBO -> Ising -> QAOA -> Bitstring -> Decoded Decisions -> Simulation -> Metrics
"""

import unittest
import config
from simulation.network import TrafficNetwork
from simulation.traffic import TrafficSimulator
from simulation.events import EventManager
from optimization.qubo import TrafficQUBO
from optimization.ising import qubo_to_ising
from optimization.qaoa_qiskit import QAOAOptimizerQiskit
from optimization.qaoa_pennylane import QAOAOptimizerPennyLane
from optimization.classical import FixedTimeController, RuleBasedAdaptiveController
from emergency.corridor import EmergencyCorridor
from metrics.evaluation import MetricsEvaluator

class TestEndToEndPipeline(unittest.TestCase):
    def setUp(self):
        config.set_seed()
        self.net = TrafficNetwork()
        self.sim = TrafficSimulator(self.net)
        self.events = EventManager(self.net)
        self.corridor = EmergencyCorridor(self.net)
        self.metrics = MetricsEvaluator(mode_name="Hybrid QAOA")

    def test_full_pipeline_qiskit(self):
        # 1. Step simulation to generate initial traffic
        step_data = self.sim.step()
        self.assertGreater(step_data['total_queue'], 0)

        # 2. Trigger congestion event
        self.events.trigger_sudden_congestion(['B', 'E'], extra_vehicles=10)

        # 3. Formulate QUBO
        qubo = TrafficQUBO(self.net)
        Q, meta = qubo.build_qubo_matrix()
        self.assertIn((1, 1), Q) # Node B linear term

        # 4. Map to Ising
        h, J, offset = qubo_to_ising(Q, num_variables=6)
        self.assertGreater(len(h), 0)

        # 5. Solve via Qiskit QAOA
        qaoa_qiskit = QAOAOptimizerQiskit(reps=1, shots=256)
        res_qiskit = qaoa_qiskit.optimize(h, J, offset, num_qubits=6)
        bitstring = res_qiskit['best_bitstring']
        self.assertEqual(len(bitstring), 6)

        # 6. Decode bitstring to signal decisions
        decisions = qubo.decode_solution(bitstring)
        self.assertEqual(len(decisions), 6)

        # 7. Apply decisions to road network
        for node, bit in decisions.items():
            self.net.set_signal(node, bit)

        # 8. Step simulation with optimized signals
        new_step_data = self.sim.step()

        # 9. Record metrics
        self.metrics.record_step(
            step=1,
            total_queue=new_step_data['total_queue'],
            avg_wait=new_step_data['avg_wait_time'],
            throughput=new_step_data['step_throughput'],
            current_decisions=decisions
        )

        summary = self.metrics.get_summary()
        self.assertGreater(summary['total_steps'], 0)
        self.assertGreater(summary['total_fuel_liters'], 0.0)
        self.assertGreater(summary['total_co2_kg'], 0.0)

    def test_full_pipeline_pennylane(self):
        # Verify PennyLane solver on the same pipeline
        self.sim.step()
        qubo = TrafficQUBO(self.net)
        Q, _ = qubo.build_qubo_matrix()
        h, J, offset = qubo_to_ising(Q, num_variables=6)

        qaoa_pennylane = QAOAOptimizerPennyLane(reps=1, shots=256)
        res_pl = qaoa_pennylane.optimize(h, J, offset, num_qubits=6)

        bitstring = res_pl['best_bitstring']
        self.assertEqual(len(bitstring), 6)
        decisions = qubo.decode_solution(bitstring)
        for node, bit in decisions.items():
            self.net.set_signal(node, bit)

        self.sim.step()

if __name__ == '__main__':
    unittest.main()
