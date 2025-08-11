from .base_controller import BaseController, TLSObservation, ControllerAction
from . import register

@register("fixed_time")
class FixedTime(BaseController):
    decision_hz = 0.2 # quyết định mỗi 5 giây
    def decide(self, obs: TLSObservation) -> ControllerAction:
        # Do nothing; keep whatever default program/phases SUMO uses.
        return ControllerAction(kind="HOLD", reason="fixed_time_hold", next_in=5.0)  # hỏi lại sau 5s cho nhẹ IPC
