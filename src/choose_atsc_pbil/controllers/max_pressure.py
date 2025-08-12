# src/controllers/max_pressure.py
from .base_controller import BaseController
from . import register

@register("max_pressure")
class MaxPressure(BaseController):
    def __init__(self, tls_id: str, **params):
        super().__init__(tls_id, **params)
        self.tls_info = params.get("tls_info", {})
        self.sample_interval = params.get("sample_interval", 10.0)
        self.cycle_time = self.tls_info["cycle"]
        self.phases = self.tls_info["phases"]
        self.lost_time = self._calculate_lost_time()

    def _calculate_lost_time(self):
        lost_time = 0
        for phase in self.phases:
            if phase["type"] != "green":
                lost_time += phase["duration"]
        return lost_time

    def _optimize_signal_plan(self):
        phases_pressure = self._calculate_phases_pressure()
        greentimes = self._initialize_greentime(phases_pressure)
        constrained_greentimes = self._constrain_greentimes(greentimes)

        # Update the plan with the optimized green times
        for i, phase in enumerate(self.node_data.get_signal_plan().get_phases()):
            phase.set_greentime(constrained_greentimes[i])
            phase.set_duration(constrained_greentimes[i] + self.lost_time / len(self.node_data.get_signal_plan().get_phases()))  # Distribute lost time evenly
    
        return self.node_data.get_signal_plan().get_phases()

    def action(self, iface, t):

        if int(t) % int(self.sample_interval) == 0:
            # Perform sampling action
            pass

        if int(t) % int(self.cycle_time) == 0:
            # Perform decision action
            splits = iface.get_splits(self.tls_id)
            new_durations = [10,3,1,20,3,1]
            for i, phase in enumerate(splits.phases):
                phase.duration = new_durations[i]
            iface.set_splits(self.tls_id, splits)
            print(f"ID: {self.tls_id} -> SPLIT")

        # calculate next time action
        next_sampling = (int(t) // int(self.sample_interval) + 1) * self.sample_interval
        next_decision = (int(t) // int(self.cycle_time) + 1) * self.cycle_time
        next_time = min(next_sampling, next_decision)

        return next_time


