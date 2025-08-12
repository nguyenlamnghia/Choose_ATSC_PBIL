# src/controllers/webster.py
from .base_controller import BaseController, TLSObservation, ControllerAction
from . import register

@register("webster")
class Webster(BaseController):
    def decide(self, obs: TLSObservation) -> ControllerAction:
        # tính C*, splits theo Webster từ lưu lượng lịch sử/hiện tại
        C = 90.0
        splits = {0: 30.0, 2: 30.0}  # ví dụ: pha 0 và 2 có green 30s
        return ControllerAction(kind="SET_SPLITS", cycle_length=C, splits=splits, reason="webster")