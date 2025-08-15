# src/controllers/max_pressure.py
from .base_controller import BaseController
from . import register
import numpy as np
import math

@register("max_pressure")
class MaxPressure(BaseController):
    def __init__(self, tls_id: str, iface, **params):
        super().__init__(tls_id, iface, **params)
        self.tls_info = params.get("tls_info", {})
        self.sample_interval = params.get("sample_interval", 10.0)
        self.cycling = params.get("cycling", "linear")
        self.cycle_time = self.tls_info["cycle"]
        self.phases = self.tls_info["phases"]
        self.edges = self.tls_info["edges"]
        self.movements = self.tls_info["movements"]
        self.lost_time = self._calculate_lost_time()

    def start(self):
        # Initialize any necessary data structures or states

        # init cache edge occupancy
        self.cache_edges_occupancy = {}
        for edge in self.edges:
            self.cache_edges_occupancy[edge] = []

    def _sample_action(self):
        for edge, data in self.edges.items():
            edge_occupancy = []
            for detector in data["detector"]:
                edge_occupancy.append(self.iface.get_lanearea_occupancy(detector))

            # if edge have detector
            if edge_occupancy:
                self.cache_edges_occupancy[edge].append(np.mean(edge_occupancy))
            # if edge has no detector
            else:
                self.cache_edges_occupancy[edge].append(np.float64(0))
                # Print Warning
                # print(f"Warning: No detector found for edge {edge}")

    def _set_split(self, final_greentimes, splits):
        splits = self.iface.get_tls_splits(self.tls_id)
        for i, duration in final_greentimes.items():
            splits.phases[int(i)].duration = duration
        self.iface.set_tls_splits(self.tls_id, splits)

    def _decide_action(self):
        # Implement your decision-making logic here
        phases_pressure = self._calculate_phases_pressure()
        greentimes = self._initialize_greentime(phases_pressure)
        constrained_greentimes = self._constrain_greentimes(greentimes)

        final_greentimes = constrained_greentimes

        # Update the plan with the optimized green times
        self._set_split(final_greentimes, self.iface.get_tls_splits(self.tls_id))
        print(f"Time: {self.iface.get_time()} - ID: {self.tls_id} -> MAX PRESSURE: SET CYCLE {final_greentimes}")

        # reset cache
        for edge in self.edges:
            self.cache_edges_occupancy[edge] = []

    def _calculate_lost_time(self):
        lost_time = 0
        splits = self.iface.get_tls_splits(self.tls_id)
        # Calculate lost time based on non-green phases
        for phase in splits.phases:
            state = phase.state.lower()
            # Count lost time for phases that are not green or are red without green
            # Check if duration < 15 is yellow phase and all red phase
            if phase.duration < 15:
                lost_time += phase.duration
        return lost_time

    def _calculate_phases_pressure(self):
        # calculate edges occupancy
        edges_occupancy = {}
        for edge in self.edges:
            edges_occupancy[edge] = np.mean(self.cache_edges_occupancy[edge])

        # calculate movements pressure
        movements_pressure = {}
        for from_edge, data in self.movements.items():
            # Get sum out_edge by ratio
            for out_edge, ratio in data.items():
                out_pressure = edges_occupancy[out_edge] * ratio
            movements_pressure[from_edge] = (edges_occupancy[from_edge] - out_pressure) * self.edges[from_edge]["sat_flow"]
        
        # calculate phases pressure
        phases_pressure = {}
        for phase, data in self.phases.items():
            phase_pressure = 0
            for movement in data["movements"]:
                phase_pressure += movements_pressure.get(movement[0], 0) * self.movements[movement[0]][movement[1]]
            phases_pressure[phase] = max(phase_pressure, 0)

        return phases_pressure

    def _initialize_greentime(self, phases_pressure):
        """Initialize green time for each phase based on pressure - simplified."""
        total_greentime = self.cycle_time - self.lost_time
        total_phase_pressures = sum(phases_pressure.values())
        greentimes = {}
        # Handle zero or negative pressure
        if total_phase_pressures <= 0:
            # Equal distribution when no pressure
            equal_greentime = total_greentime / len(phases_pressure)
            for phase in phases_pressure:
                greentimes[phase] = equal_greentime
        else:
            # Proportional distribution based on pressure
            
            if self.cycling == "linear":
                for phase in phases_pressure:
                    greentimes[phase] = (phases_pressure[phase] / total_phase_pressures) * total_greentime
            elif self.cycling == "exponential":
                exp_pressures = [math.exp(phases_pressure[phase] / total_phase_pressures) for phase in phases_pressure]
                total_exp_pressures = sum(exp_pressures)
                for i, phase in enumerate(phases_pressure):
                    greentimes[phase] = (exp_pressures[i] / total_exp_pressures) * total_greentime

            else:
                raise ValueError("Cycling method not recognized. Use 'linear' or 'exponential'.")
        return greentimes
        
    
    # Anh Kiên Code
    def _constrain_greentimes(self, greentimes):
        """Constrain green times using simple and efficient algorithm."""
        phases = self.phases
        greentimes_arr = greentimes.values()
        # Get constraints
        min_greentimes = [data["min-green"] for phase, data in phases.items()]
        max_greentimes = [data["max-green"] for phase, data in phases.items()]
        target_sum = self.cycle_time - self.lost_time
        
        # Validate feasibility
        min_sum = sum(min_greentimes)
        max_sum = sum(max_greentimes)
        
        if min_sum > target_sum:
            print(f"ERROR: Minimum sum ({min_sum}) > target ({target_sum}), using minimum values")
            exit()
        if max_sum < target_sum:
            print(f"ERROR: Maximum sum ({max_sum}) < target ({target_sum}), using maximum values")
            exit()
        
        # Simple proportional scaling with constraint enforcement
        result = []
        total_initial = sum(greentimes_arr) if sum(greentimes_arr) > 0 else len(greentimes_arr)

        # Scale proportionally and apply constraints
        for i, greentime in enumerate(greentimes_arr):
            scaled = (greentime / total_initial) * target_sum if total_initial > 0 else target_sum / len(greentimes_arr)
            constrained = max(min_greentimes[i], min(max_greentimes[i], int(round(scaled))))
            result.append(constrained)
        
        # Adjust to meet exact target sum
        current_sum = sum(result)
        diff = target_sum - current_sum
        
        # Distribute difference
        attempts = 0
        while diff != 0 and attempts < target_sum:  # Prevent infinite loop
            if diff > 0:  # Need to add time
                for i in range(len(result)):
                    if result[i] < max_greentimes[i] and diff > 0:
                        result[i] += 1
                        diff -= 1
            else:  # Need to remove time
                for i in range(len(result)):
                    if result[i] > min_greentimes[i] and diff < 0:
                        result[i] -= 1
                        diff += 1
            attempts += 1
        
        # convert greentimes_arr to greentimes
        for k, v in zip(greentimes.keys(), result):
            greentimes[k] = v
        return greentimes

    def action(self, t):
        # Perform action every sample interval
        if int(t) % int(self.sample_interval) == 0:
            # print(f"--- Sample for TLS ID {self.tls_id}")
            self._sample_action()

        # Perform action every cycle time
        if int(t) % int(self.cycle_time) == 0:
            # print(f"--- Cycle for TLS ID {self.tls_id}")
            self._decide_action()
            
        # calculate next time action
        next_sampling = (int(t) // int(self.sample_interval) + 1) * self.sample_interval
        next_decision = (int(t) // int(self.cycle_time) + 1) * self.cycle_time
        next_time = min(next_sampling, next_decision)

        return next_time


