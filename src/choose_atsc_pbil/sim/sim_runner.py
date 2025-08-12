import time, json, os, random
from datetime import datetime
from typing import Dict
import numpy as np

from .traci_interface import TraciIF
from ..controllers import build as build_controller
# from ..controllers.base_controller import TLSObservation, ControllerAction

class SumoSimRunner:
    def __init__(self, sumo_cfg: dict, controller_plan: dict, net_info: dict):
        self.sumo_cfg = sumo_cfg
        self.controller_plan = controller_plan
        self.net_info = net_info
        self.iface = TraciIF(sumo_cfg)
        self.controllers = {}
        self.pbil_data_collection = []

    # Get data for PBIL learning
    def get_data_for_pbil(self):

        # By occupancy
        # edges = self.iface.get_list_edge()
        # total_occupancy = 0
        # for edge in edges:
        #     total_occupancy += self.iface.get_edge_occupancy(edge)

        # average_occupancy = total_occupancy / len(edges) if edges else 0
        # return average_occupancy
    
        # By total vehicle
        return self.iface.get_total_vehicle()

    def _controller_for(self, tls_id: str, adaptive_mask: dict):
        # For Adaptive
        if adaptive_mask.get(tls_id):
            spec = self.controller_plan[adaptive_mask.get(tls_id)]
            params = dict(spec.get("params", {}))

            # Bơm tls_info từ net vào cho Adaptive
            tls_info = self.net_info["tls"][tls_id]
            params.setdefault("tls_info", tls_info)
            return build_controller(spec["name"], tls_id, **params)
        # For default
        spec = self.controller_plan["default"]
        params = dict(spec.get("params", {}))
        return build_controller(spec["name"], tls_id, **params)

    def run(self, adaptive_mask: Dict[str,bool], sample_interval: float) -> dict:
        self.iface.start()
        try:
            tls_ids = self.iface.list_tls_ids()

            # khởi tạo controller
            for tls_id in tls_ids:
                ctrl = self._controller_for(tls_id, adaptive_mask)
                self.controllers[tls_id] = ctrl

            t = self.iface.begin_time()
            end = self.iface.end_time()

            # arr save tls time next action
            next_action_list = {tls_id: t for tls_id in tls_ids}
            while t < end:

                # get next time sampling
                next_sampling = (int(t) // int(sample_interval) + 1) * sample_interval

                # get time next update
                next_action = min(next_action_list.values())

                # Choose next_sampling or next_action
                next_time = min(next_sampling, next_action)
                self.iface.step_to(next_time)
                t = next_time

                if next_time == next_action:
                    # get tls_ids next update
                    next_tls_ids = [tls_id for tls_id, action_time in next_action_list.items() if action_time == next_action]

                    for tls_id in next_tls_ids:
                        next_update = self.controllers[tls_id].action(self.iface, t)
                        next_action_list[tls_id] = next_update
                
                if next_time == next_sampling:
                    self.pbil_data_collection.append(self.get_data_for_pbil())

            print(np.mean(self.pbil_data_collection) if self.pbil_data_collection else 0)
            return np.mean(self.pbil_data_collection) if self.pbil_data_collection else 0
        finally:
            self.iface.close()

    # def _apply_action(self, tls_id: str, action: ControllerAction):
    #     if action.kind == "HOLD":
    #         return
    #     elif action.kind == "SWITCH":
    #         self.iface.safe_switch(tls_id, next_phase=int(action.next_phase or 0))
    #     elif action.kind == "SET_SPLITS":
    #         if action.cycle_length and action.splits:
    #             self.iface.set_splits(tls_id, action.cycle_length, action.splits)
    #     elif action.kind == "SET_PROGRAM":
    #         pass
