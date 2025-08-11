# src/controllers/max_pressure.py
from .base_controller import BaseController, TLSObservation, ControllerAction
from . import register

@register("max_pressure")
class MaxPressure(BaseController):
    def __init__(self, tls_id: str, **params):
        super().__init__(tls_id, **params)
        self.tls_info = params.get("tls_info", {})
    decision_hz = 1.0
    def decide(self, obs: TLSObservation) -> ControllerAction:
        # Stub đơn giản: nếu đủ min_green thì chuyển pha kế; ngược lại giữ
        if obs["phase_elapsed"] >= obs["min_green"] and len(obs["phases"]) > 0:
            next_phase = (obs["phase_index"] + 1) % len(obs["phases"])
            # sau khi SWITCH thì ít nhất chờ thêm min_green mới xét tiếp
            return ControllerAction(kind="SWITCH",
                                    next_phase=next_phase,
                                    reason="mp_switch_min_green_reached",
                                    next_in=obs["min_green"])
        # chưa đủ min_green: hẹn kiểm tra lại phần còn thiếu (tối thiểu 0.5s)
        remain = max(0.5, obs["min_green"] - obs["phase_elapsed"])
        return ControllerAction(kind="HOLD",
                                reason="mp_hold_wait_min_green",
                                next_in=remain)

