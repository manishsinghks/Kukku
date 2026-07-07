"""System status via psutil — shared by the agent tool and the dashboard."""
from __future__ import annotations

import time
from typing import Any

import psutil

_START = time.time()


def system_status() -> dict[str, Any]:
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.3),
        "cpu_count": psutil.cpu_count(),
        "ram_percent": vm.percent,
        "ram_used_gb": round(vm.used / 1e9, 2),
        "ram_total_gb": round(vm.total / 1e9, 2),
        "disk_percent": disk.percent,
        "disk_used_gb": round(disk.used / 1e9, 2),
        "disk_total_gb": round(disk.total / 1e9, 2),
        "uptime_s": int(time.time() - _START),
        "boot_time": psutil.boot_time(),
    }
