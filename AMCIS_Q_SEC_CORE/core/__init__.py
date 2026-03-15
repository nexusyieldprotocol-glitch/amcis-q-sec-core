"""
AMCIS Security Core Module
===========================

Core security framework components for AMCIS_Q_SEC_CORE.
Provides kernel orchestration, trust evaluation, anomaly detection,
intrusion response, and integrity monitoring capabilities.

Version: 1.0.0
Author: AMCIS Security Team
"""

from .amcis_kernel import AMCISKernel, KernelState
from .amcis_trust_engine import TrustEngine, TrustScore
from .amcis_anomaly_engine import AnomalyEngine, AnomalyReport
from .amcis_response_engine import ResponseEngine, ResponseAction
from .amcis_integrity_monitor import IntegrityMonitor, IntegrityReport
from .amcis_exceptions import (
    AMCISException, ErrorCode, CryptoException, TrustException,
    NetworkException, EDRException, SupplyChainException,
    AISecurityException, ComplianceException, StorageException,
    ErrorContext, Result, error_handler
)
from .amcis_error_utils import (
    SafeCall, safe_method, retry, batch_process,
    validate_not_none, validate_not_empty, validate_type, validate_range,
    timing_context, ignore_errors
)

__all__ = [
    # Core components
    "AMCISKernel", "KernelState",
    "TrustEngine", "TrustScore",
    "AnomalyEngine", "AnomalyReport",
    "ResponseEngine", "ResponseAction",
    "IntegrityMonitor", "IntegrityReport",
    # Exceptions
    "AMCISException", "ErrorCode",
    "CryptoException", "TrustException", "NetworkException",
    "EDRException", "SupplyChainException", "AISecurityException",
    "ComplianceException", "StorageException",
    "ErrorContext", "Result", "error_handler",
    # Utilities
    "SafeCall", "safe_method", "retry", "batch_process",
    "validate_not_none", "validate_not_empty", "validate_type", "validate_range",
    "timing_context", "ignore_errors",
]

__version__ = "1.0.0"
