# src/controllers/base_controller.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Literal
from abc import ABC, abstractmethod

class BaseController(ABC):
    """Mỗi TLS một instance controller."""

    def __init__(self, tls_id: str, iface, **params):
        self.tls_id = tls_id
        self.cfg = params
        self.iface = iface
    # def on_reset(self, obs: TLSObservation) -> None: ...
    def on_close(self) -> None: ...

    @abstractmethod
    def action(self, iface, t) -> float:
        pass

    @abstractmethod
    def start(self, iface) -> None:
        pass

    # Cho controller học thích nghi theo feedback (tuỳ chọn)
    def update(self, feedback: dict) -> None:
        pass
