"""
AMCIS Endpoint Detection and Response (EDR) Module
===================================================

Terminal-native EDR capabilities for AMCIS_Q_SEC_CORE.
Provides process monitoring, memory inspection, file integrity,
and system call analysis.

NIST Alignment: SP 800-53 (SI-4 Information System Monitoring)
"""

from .amcis_process_graph import ProcessGraph, ProcessNode
from .amcis_memory_inspector import MemoryInspector, MemoryRegion
from .amcis_file_integrity import FileIntegrityMonitor, FileBaseline
from .amcis_syscall_monitor import SyscallMonitor, SyscallEvent

__all__ = [
    "ProcessGraph",
    "ProcessNode",
    "MemoryInspector",
    "MemoryRegion",
    "FileIntegrityMonitor",
    "FileBaseline",
    "SyscallMonitor",
    "SyscallEvent",
]

__version__ = "1.0.0"
