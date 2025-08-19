import time, json, os, random
from datetime import datetime
from typing import Dict
import numpy as np

from .traci_interface import TraciIF
from ..controllers import build as build_controller
import logging

logger = logging.getLogger(__name__)

class SumoSimRunner:
    def __init__(self, sumo_cfg: dict, controller_plan: dict, pbil_cfg: dict, net_info: dict):
        self.sumo_cfg = sumo_cfg
        self.controller_plan = controller_plan
        self.pbil_cfg = pbil_cfg
        self.net_info = net_info
        self.iface = TraciIF(sumo_cfg)
        self.controllers = {}

    # Collect data
    def _collect_data(self, collected_data):
        # Collect Total Vehicle
        collected_data["total_vehicle"].append(self.iface.get_total_vehicle())

        # Collect Average Occupancy
        edges = self.iface.get_list_edge()
        total_occupancy = 0
        for edge in edges:
            total_occupancy += self.iface.get_edge_occupancy(edge)

        average_occupancy = total_occupancy / len(edges) if edges else 0
        collected_data["average_occupancy"].append(average_occupancy)


        return collected_data

    def _controller_for(self, tls_id: str, adaptive_mask: dict):
        # For Adaptive
        if adaptive_mask.get(tls_id):
            # spec = self.controller_plan[adaptive_mask.get(tls_id)]
            spec = self.controller_plan[self.net_info["tls"][tls_id]["controller"]]
            params = dict(spec.get("params", {}))

            # Bơm tls_info từ net vào cho Adaptive
            tls_info = self.net_info["tls"][tls_id]
            params.setdefault("tls_info", tls_info)
            return build_controller(spec["name"], tls_id, self.iface, **params)
        
        # For default
        spec = self.controller_plan["default"]
        params = dict(spec.get("params", {}))
        return build_controller(spec["name"], tls_id, self.iface, **params)

    def run(self, adaptive_mask: Dict[str,bool]) -> dict:

        # Init collected data
        collected_data = {
            "total_vehicle": [],
            "average_occupancy": []
        }

        self.iface.start()
        try:
            tls_ids = self.iface.list_tls_ids()

            # Validate tls if tls not exists
            for tls_id in adaptive_mask.keys():
                if tls_id not in tls_ids:
                    logger.warning("TLS ID %s not found in SUMO.", tls_id)

            # khởi tạo controller
            for tls_id in tls_ids:
                ctrl = self._controller_for(tls_id, adaptive_mask)
                self.controllers[tls_id] = ctrl

                # start controller
                self.controllers[tls_id].start()

            # Get sample interval PBIL
            sample_interval  = self.pbil_cfg["sample_interval"]

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
                        next_update = self.controllers[tls_id].action(t)
                        next_action_list[tls_id] = next_update
                
                if next_time == next_sampling:
                    self._collect_data(collected_data)

            return collected_data
        except Exception as e:
            logger.exception("Error occurred during simulation: %s", e)
        finally:
            self.iface.close()

