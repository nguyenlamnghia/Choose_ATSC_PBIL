# src/controllers/base_controller.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Literal
from abc import ABC, abstractmethod

# Một class quan sát trạng thái của một đèn giao thông
@dataclass
class TLSObservation:
    tls_id: str
    sim_time: float
    phase_index: int                 # pha hiện tại
    phase_elapsed: float             # thời gian đã ở pha hiện tại
    phases: List[str]                # mask tín hiệu (SUMO’s "rGrg...")
    min_green: float                 # ràng buộc tối thiểu
    yellow: float
    all_red: float
    incoming_lanes: List[str]
    outgoing_lanes: List[str]
    queues_in: Dict[str, float]      # hàng đợi từng lane vào
    queues_out: Dict[str, float]     # hàng đợi từng lane ra
    densities_in: Dict[str, float]   # (optional)
    densities_out: Dict[str, float]  # (optional)

# Một action "chuẩn hoá" để runner áp dụng đúng cách, an toàn pha vàng/đỏ
@dataclass
class ControllerAction:
    kind: Literal["HOLD", "SWITCH", "SET_SPLITS", "SET_PROGRAM"]
    next_phase: Optional[int] = None
    cycle_length: Optional[float] = None
    splits: Optional[Dict[int, float]] = None # example: {0: 30.0, 1: 30.0}
    reason: Optional[str] = None
    next_in: Optional[float] = None   # <-- mới: hẹn lần quyết định tới

class BaseController(ABC):
    """Mỗi TLS một instance controller."""
    # Tần suất quyết định (Webster quyết định theo chu kỳ, MP theo mỗi step)
    decision_hz: float = 1.0


    def __init__(self, tls_id: str, **params):
        self.tls_id = tls_id
        self.cfg = params
    def on_reset(self, obs: TLSObservation) -> None: ...
    def on_close(self) -> None: ...

    @abstractmethod
    def decide(self, obs: TLSObservation) -> ControllerAction:
        """Không side-effect. Runner sẽ apply Action vào TraCI."""

    # Cho controller học thích nghi theo feedback (tuỳ chọn)
    def update(self, feedback: dict) -> None:
        pass
