import os
from typing import List, Dict, Optional
from dataclasses import asdict
try:
    # import traci
    from sumolib.net import readNet
    import libsumo as traci
except Exception as e:
    traci = None

# from ..controllers.base_controller import TLSObservation

class TraciIF:
    def __init__(self, sumo_cfg: dict):
        self.cfg = sumo_cfg
        self._net = None
        self._running = False
        self._begin = float(sumo_cfg.get("begin", 0))
        self._end = float(sumo_cfg.get("end", 3600))
        self._step = float(sumo_cfg.get("step_length", 0.1))
        self._snapshot_interval = float(sumo_cfg.get("snapshot_interval", 1.0))

    def _ensure_import(self):
        if traci is None:
            raise ImportError("Could not import traci/sumolib. Ensure SUMO is installed and PYTHONPATH is set.")

    def start(self):
        self._ensure_import()

        # Determine gui mode
        sumo_gui = "sumo-gui" if self.cfg["gui"] else "sumo"

        # Configure SUMO command
        sumoCmd = [
            sumo_gui,
            "--no-warnings",
            "--start",  # start simulation immediately
            "-c", self.cfg["sumocfg"],
            "--step-length", str(self._step),
            "--lateral-resolution", str(self.cfg["lateral_resolution"])
        ]

        add = self.cfg.get("add_file")
        if add:
            sumoCmd += ["-a", add]
        traci.start(sumoCmd)
        self._running = True

    def close(self):
        if self._running:
            traci.close()
            self._running = False

    def step(self):
        traci.simulationStep()

    def step_to(self, t_abs: float):
        # SUMO cho phép simulationStep(time) nhảy tới absolute time
        traci.simulationStep(t_abs)

    def begin_time(self)->float:
        return self._begin

    def end_time(self)->float:
        return self._end

    def list_tls_ids(self)->List[str]:
        return list(traci.trafficlight.getIDList())
    
    def get_current_phase(self, tls_id: str) -> int:
        """Lấy pha hiện tại của đèn giao thông."""
        return traci.trafficlight.getPhase(tls_id)

    def get_time(self) -> float:
        """Lấy thời gian mô phỏng hiện tại."""
        return traci.simulation.getTime()
    
    def get_list_edge(self):
        return traci.edge.getIDList()

    def get_edge_occupancy(self, edge_id: str) -> float:
        """Lấy thông tin lưu lượng của một đoạn đường."""
        return traci.edge.getLastStepOccupancy(edge_id)

    def get_total_vehicle(self):
        """Lấy tổng số phương tiện trên một đoạn đường."""
        return traci.vehicle.getIDCount()

    def set_phase(self, tls_id: str, phase_index: int):
        """Set the current phase of the traffic light."""
        traci.trafficlight.setPhase(tls_id, phase_index)

    def set_duration(self, tls_id: str, duration: float):
        """Set the duration of the current phase."""
        # Note: This is a simplified version, real implementation should handle yellow/all-red phases
        traci.trafficlight.setPhaseDuration(tls_id, duration)

    def _phase_elapsed(self, tls_id: str) -> float:
        return traci.trafficlight.getPhaseDuration(tls_id) - traci.trafficlight.getNextSwitch(tls_id) + traci.simulation.getTime()

    def observe_tls(self, tls_id: str, ctrl_name: str):

        # handle for max_pressure
        if ctrl_name == "max_pressure":
            pi = traci.trafficlight.getPhase(tls_id) # Get current phase index. Ex: 0
            phases = [p.state for p in traci.trafficlight.getCompleteRedYellowGreenDefinition(tls_id)[0].phases] # Get all phase states. Ex: 
            elapsed = max(0.0, float(traci.trafficlight.getPhaseDuration(tls_id) - traci.trafficlight.getNextSwitch(tls_id) + traci.simulation.getTime()))
            lanes_in = traci.trafficlight.getControlledLanes(tls_id)
            # crude outgoing lanes via links
            links = traci.trafficlight.getControlledLinks(tls_id)
            lanes_out = list({toLane for group in links for (_from, toLane, _via) in group if toLane})

            # simple queues/densities
            q_in = {ln: float(traci.lane.getLastStepVehicleNumber(ln)) for ln in lanes_in}
            q_out = {ln: float(traci.lane.getLastStepVehicleNumber(ln)) for ln in lanes_out}
            d_in = {ln: float(traci.lane.getLastStepOccupancy(ln)) for ln in lanes_in}
            d_out = {ln: float(traci.lane.getLastStepOccupancy(ln)) for ln in lanes_out}
            return {
                "phase_index": pi,
                "phase_elapsed": elapsed,
                "phases": phases,
                "min_green": float(self.cfg.get("min_green", 5.0)),
                "yellow": float(self.cfg.get("yellow", 3.0)),
                "all_red": float(self.cfg.get("all_red", 1.0)),
                "incoming_lanes": lanes_in,
                "outgoing_lanes": lanes_out,
                "queues_in": q_in,
                "queues_out": q_out,
                "densities_in": d_in,
                "densities_out": d_out,
            }
        elif ctrl_name == "webster":
            # Implement observation extraction for Webster controller
            return {}
        else:
            return {}

    def safe_switch(self, tls_id: str, next_phase: int, min_green: float, yellow: float, all_red: float):
        # Very simplified: directly set phase (real implementation should insert yellow/all-red safety)
        # traci.trafficlight.setPhase(tls_id, int(next_phase))
        pass

    def set_splits(self, tls_id: str, splits):
        # Simplified: set phase duration for the current cycle; full implementation would rebuild a program
        # Here we no-op to keep it safe for a scaffold; SUMO program editing is non-trivial.
        traci.trafficlight.setCompleteRedYellowGreenDefinition(tls_id, splits)

    def get_splits(self, tls_id):
        return traci.trafficlight.getCompleteRedYellowGreenDefinition(tls_id)[0]

    def snapshot_network_density(self) -> float:
        lanes = traci.lane.getIDList()
        if not lanes:
            return 0.0
        occ = [float(traci.lane.getLastStepOccupancy(l)) for l in lanes]
        return float(sum(occ) / len(occ))
