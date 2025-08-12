# src/controllers/__init__.py
from typing import Dict, Type
from .base_controller import BaseController
REGISTRY: Dict[str, Type[BaseController]] = {}

def register(name: str):
    def deco(cls):
        REGISTRY[name] = cls
        return cls
    return deco

def build(name: str, tls_id: str, iface, **params) -> BaseController:
    if name not in REGISTRY:
        raise KeyError(f"Unknown controller: {name}")
    return REGISTRY[name](tls_id=tls_id, iface=iface, **params)

# 👇 Thêm dòng này (eager import để chạy decorator @register)
from . import fixed_time, max_pressure # noqa: F401