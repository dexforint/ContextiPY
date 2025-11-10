"""Logging subsystem for Contextipy script execution.

This module provides logging utilities for tracking script execution metadata,
including run IDs, timestamps, status, actions, and I/O captures. It integrates
with the execution runtime hooks and provides query APIs for historical runs.
"""

from .logger import ExecutionLog, ExecutionLogger

__all__ = [
    "ExecutionLogger",
    "ExecutionLog",
]
