import time, json, os, random
from datetime import datetime
from typing import Dict
import numpy as np

from .traci_interface import TraciIF
from ..controllers import build as build_controller
from ..controllers.base_controller import TLSObservation, ControllerAction

class SumoSimRunner:
    def __init__(self, sumo_cfg: dict, controller_plan: dict, net_info: dict):
        self.sumo_cfg = sumo_cfg
        self.controller_plan = controller_plan
        self.net_info = net_info
        self.iface = TraciIF(sumo_cfg)
        self.controllers = {}
        self.decision_clock = {}
        self.snapshot_interval = float(sumo_cfg.get("snapshot_interval", 10.0))

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

        # if adaptive_mask.get(tls_id) == "max_pressure":
        #     spec = self.controller_plan["max_pressure"]
        #     params = dict(spec.get("params", {}))

        #     # Bơm tls_info từ net vào cho max_pressure
        #     tls_info = self.net_info["tls"][tls_id]
        #     params.setdefault("tls_info", tls_info)
        # else:
        #     spec = self.controller_plan["default"]
        #     params = dict(spec.get("params", {}))
        # return build_controller(spec["name"], tls_id, **params)

    def run(self, adaptive_mask: Dict[str,bool]) -> dict:
        self.iface.start()
        try:
            tls_ids = self.iface.list_tls_ids()
            # khởi tạo controller + lịch lần quyết định đầu
            for tls_id in tls_ids:
                ctrl = self._controller_for(tls_id, adaptive_mask)
                self.controllers[tls_id] = ctrl

            t = self.iface.begin_time()
            end = self.iface.end_time()
            next_decision = {tls_id: t for tls_id in tls_ids}
            next_snapshot = t + self.snapshot_interval

            metrics = []
            while t < end:
                # mốc tiếp theo = min( mọi next_decision, next_snapshot, end )
                next_t = min([next_snapshot, end] + list(next_decision.values()))
                self.iface.step_to(next_t)     # <-- nhảy trực tiếp
                t = next_t

                # 1) xử lý các TLS đến hạn quyết định (dùng ngưỡng eps tránh lỗi số)
                eps = 1e-9
                due_tls = [k for k,v in next_decision.items() if abs(v - t) <= eps]
                for tls_id in due_tls:
                    ctrl_name = adaptive_mask.get(tls_id) or "default"
                    # Xử lý các tls có kiểu max_pressure
                    if adaptive_mask.get(tls_id) != "default":
                        # chỉ observe TLS này, không quét tất cả
                        obs = self.iface.observe_tls(tls_id,ctrl_name)
                        action = self.controllers[tls_id].decide(obs)
                        self._apply_action(tls_id, action, obs)

                    # Xử lý các tls có kiểu webster
                    if adaptive_mask.get(tls_id) == "webster":
                        pass

                    # lịch lần sau: ưu tiên action.next_in; fallback theo decision_hz
                    dt = action.next_in
                    if dt is None or dt <= 0:
                        hz = max(1e-6, getattr(self.controllers[tls_id], "decision_hz", 1.0))
                        dt = 1.0 / hz

                    # bảo đảm sau SWITCH thì ít nhất giữ min_green
                    if action.kind == "SWITCH":
                        dt = max(dt, obs["min_green"])

                    next_decision[tls_id] = t + dt

                # 2) snapshot nếu tới hạn
                if t >= next_snapshot - eps:
                    metrics.append(self.iface.snapshot_network_density())
                    next_snapshot += self.snapshot_interval
            return {"avg_network_density": float(sum(metrics)/len(metrics)) if metrics else 0.0}
        finally:
            self.iface.close()

    def _apply_action(self, tls_id: str, action: ControllerAction, obs: TLSObservation):
        if action.kind == "HOLD":
            return
        elif action.kind == "SWITCH":
            self.iface.safe_switch(tls_id, next_phase=int(action.next_phase or 0),
                                   min_green=obs["min_green"], yellow=obs["yellow"], all_red=obs["all_red"])
        elif action.kind == "SET_SPLITS":
            if action.cycle_length and action.splits:
                self.iface.set_splits(tls_id, action.cycle_length, action.splits)
        elif action.kind == "SET_PROGRAM":
            pass
