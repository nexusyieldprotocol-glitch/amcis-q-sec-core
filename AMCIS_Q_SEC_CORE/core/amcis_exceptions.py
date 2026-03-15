"""
AMCIS Exception Hierarchy
=========================

Centralized error handling with optimized exception classes.
All exceptions derive from AMCISException for unified handling.
"""

from enum import Enum, auto
from typing import Any, Dict, Optional, List
import structlog


class ErrorCode(Enum):
    """Standardized error codes for all AMCIS components."""
    
    # General errors (1-99)
    UNKNOWN_ERROR = auto()
    INVALID_ARGUMENT = auto()
    NOT_IMPLEMENTED = auto()
    OPERATION_FAILED = auto()
    TIMEOUT_ERROR = auto()
    RESOURCE_EXHAUSTED = auto()
    
    # Crypto errors (100-199)
    CRYPTO_ERROR = auto()
    INVALID_KEY = auto()
    INVALID_SIGNATURE = auto()
    ENCRYPTION_FAILED = auto()
    DECRYPTION_FAILED = auto()
    KEY_NOT_FOUND = auto()
    KEY_ROTATION_FAILED = auto()
    HASH_VERIFICATION_FAILED = auto()
    
    # Trust/Security errors (200-299)
    TRUST_VIOLATION = auto()
    POLICY_VIOLATION = auto()
    AUTHENTICATION_FAILED = auto()
    AUTHORIZATION_FAILED = auto()
    QUARANTINE_FAILED = auto()
    
    # Network errors (300-399)
    NETWORK_ERROR = auto()
    CONNECTION_REFUSED = auto()
    CONNECTION_TIMEOUT = auto()
    INVALID_PACKET = auto()
    RATE_LIMIT_EXCEEDED = auto()
    
    # EDR errors (400-499)
    EDR_ERROR = auto()
    PROCESS_NOT_FOUND = auto()
    MEMORY_ACCESS_DENIED = auto()
    SYSCALL_MONITOR_ERROR = auto()
    
    # Supply chain errors (500-599)
    SBOM_ERROR = auto()
    DEPENDENCY_VALIDATION_FAILED = auto()
    SIGNATURE_VERIFICATION_FAILED = auto()
    
    # AI Security errors (600-699)
    AI_SECURITY_ERROR = auto()
    PROMPT_INJECTION_DETECTED = auto()
    OUTPUT_VALIDATION_FAILED = auto()
    
    # Compliance errors (700-799)
    COMPLIANCE_VIOLATION = auto()
    AUDIT_LOG_ERROR = auto()
    
    # Storage errors (800-899)
    STORAGE_ERROR = auto()
    FILE_NOT_FOUND = auto()
    PERMISSION_DENIED = auto()
    CORRUPT_DATA = auto()


class AMCISException(Exception):
    """
    Base exception for all AMCIS errors.
    
    Optimized for:
    - Minimal memory footprint
    - Fast error code lookup
    - Structured logging integration
    """
    
    __slots__ = ('error_code', 'details', 'correlation_id', '_logger')
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}
        self.correlation_id = correlation_id
        self._logger = structlog.get_logger("amcis.errors")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for serialization."""
        return {
            'error_code': self.error_code.name,
            'message': str(self),
            'details': self.details,
            'correlation_id': self.correlation_id
        }
    
    def log(self, level: str = "error") -> 'AMCISException':
        """Log exception and return self for chaining."""
        log_data = self.to_dict()
        log_method = getattr(self._logger, level)
        log_method("amcis_exception", **log_data)
        return self


# Component-specific exceptions

class CryptoException(AMCISException):
    """Cryptographic operation errors."""
    __slots__ = ()
    
    def __init__(self, message: str, **kwargs):
        if 'error_code' not in kwargs:
            kwargs['error_code'] = ErrorCode.CRYPTO_ERROR
        super().__init__(message, **kwargs)


class TrustException(AMCISException):
    """Trust engine and security policy errors."""
    __slots__ = ()
    
    def __init__(self, message: str, **kwargs):
        if 'error_code' not in kwargs:
            kwargs['error_code'] = ErrorCode.TRUST_VIOLATION
        super().__init__(message, **kwargs)


class NetworkException(AMCISException):
    """Network and microsegmentation errors."""
    __slots__ = ()
    
    def __init__(self, message: str, **kwargs):
        if 'error_code' not in kwargs:
            kwargs['error_code'] = ErrorCode.NETWORK_ERROR
        super().__init__(message, **kwargs)


class EDRException(AMCISException):
    """EDR and process monitoring errors."""
    __slots__ = ()
    
    def __init__(self, message: str, **kwargs):
        if 'error_code' not in kwargs:
            kwargs['error_code'] = ErrorCode.EDR_ERROR
        super().__init__(message, **kwargs)


class SupplyChainException(AMCISException):
    """SBOM and dependency validation errors."""
    __slots__ = ()
    
    def __init__(self, message: str, **kwargs):
        if 'error_code' not in kwargs:
            kwargs['error_code'] = ErrorCode.SBOM_ERROR
        super().__init__(message, **kwargs)


class AISecurityException(AMCISException):
    """AI security and prompt firewall errors."""
    __slots__ = ()
    
    def __init__(self, message: str, **kwargs):
        if 'error_code' not in kwargs:
            kwargs['error_code'] = ErrorCode.AI_SECURITY_ERROR
        super().__init__(message, **kwargs)


class ComplianceException(AMCISException):
    """Compliance and audit errors."""
    __slots__ = ()
    
    def __init__(self, message: str, **kwargs):
        if 'error_code' not in kwargs:
            kwargs['error_code'] = ErrorCode.COMPLIANCE_VIOLATION
        super().__init__(message, **kwargs)


class StorageException(AMCISException):
    """File and storage errors."""
    __slots__ = ()
    
    def __init__(self, message: str, **kwargs):
        if 'error_code' not in kwargs:
            kwargs['error_code'] = ErrorCode.STORAGE_ERROR
        super().__init__(message, **kwargs)


# Factory functions for common errors (optimized for speed)

def raise_invalid_argument(param: str, reason: str) -> None:
    """Raise invalid argument exception."""
    raise AMCISException(
        f"Invalid argument '{param}': {reason}",
        error_code=ErrorCode.INVALID_ARGUMENT,
        details={'parameter': param, 'reason': reason}
    )


def raise_not_found(resource_type: str, resource_id: str) -> None:
    """Raise resource not found exception."""
    raise AMCISException(
        f"{resource_type} '{resource_id}' not found",
        error_code=ErrorCode.FILE_NOT_FOUND,
        details={'resource_type': resource_type, 'resource_id': resource_id}
    )


def raise_permission_denied(operation: str, resource: str) -> None:
    """Raise permission denied exception."""
    raise AMCISException(
        f"Permission denied: cannot {operation} {resource}",
        error_code=ErrorCode.PERMISSION_DENIED,
        details={'operation': operation, 'resource': resource}
    )


def raise_timeout(operation: str, timeout_sec: float) -> None:
    """Raise timeout exception."""
    raise AMCISException(
        f"Operation '{operation}' timed out after {timeout_sec}s",
        error_code=ErrorCode.TIMEOUT_ERROR,
        details={'operation': operation, 'timeout_seconds': timeout_sec}
    )


# Error handler decorator for automatic logging and conversion

def error_handler(
    default_code: ErrorCode = ErrorCode.OPERATION_FAILED,
    log_level: str = "error",
    reraise: bool = True
):
    """
    Decorator for standardized error handling.
    
    Args:
        default_code: Default error code if exception not already AMCISException
        log_level: Log level for errors
        reraise: Whether to reraise the exception after logging
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except AMCISException:
                # Already our exception type, just re-raise
                raise
            except Exception as e:
                # Convert to AMCISException
                exc = AMCISException(
                    str(e),
                    error_code=default_code,
                    details={
                        'function': func.__name__,
                        'exception_type': type(e).__name__
                    }
                )
                exc.log(log_level)
                if reraise:
                    raise exc from e
                return None
        return wrapper
    return decorator


# Context manager for batch error handling

class ErrorContext:
    """
    Context manager for batch operations with error collection.
    Collects errors without stopping on first failure.
    """
    
    __slots__ = ('errors', 'suppress', 'logger')
    
    def __init__(self, suppress: bool = True):
        self.errors: List[AMCISException] = []
        self.suppress = suppress
        self.logger = structlog.get_logger("amcis.errors")
    
    def __enter__(self) -> 'ErrorContext':
        self.errors = []
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_val and not isinstance(exc_val, AMCISException):
            exc_val = AMCISException(
                str(exc_val),
                error_code=ErrorCode.UNKNOWN_ERROR,
                details={'exception_type': exc_type.__name__ if exc_type else None}
            )
        if exc_val:
            self.errors.append(exc_val)
        return self.suppress
    
    def add_error(self, message: str, code: ErrorCode = ErrorCode.OPERATION_FAILED, **details) -> None:
        """Add an error to the collection."""
        exc = AMCISException(message, error_code=code, details=details)
        exc.log()
        self.errors.append(exc)
    
    def has_errors(self) -> bool:
        """Check if any errors occurred."""
        return len(self.errors) > 0
    
    def raise_if_errors(self) -> None:
        """Raise a composite exception if errors exist."""
        if self.has_errors():
            raise AMCISException(
                f"Batch operation failed with {len(self.errors)} errors",
                error_code=ErrorCode.OPERATION_FAILED,
                details={'errors': [e.to_dict() for e in self.errors]}
            )


# Result type for operations that may fail (Rust-like)

class Result:
    """
    Result type for explicit error handling without exceptions.
    More efficient than try/except for expected failures.
    """
    
    __slots__ = ('_value', '_error', '_is_ok')
    
    def __init__(self):
        self._value: Any = None
        self._error: Optional[AMCISException] = None
        self._is_ok: bool = True
    
    @staticmethod
    def ok(value: Any) -> 'Result':
        """Create success result."""
        r = Result()
        r._value = value
        r._is_ok = True
        return r
    
    @staticmethod
    def err(message: str, code: ErrorCode = ErrorCode.OPERATION_FAILED, **details) -> 'Result':
        """Create error result."""
        r = Result()
        r._error = AMCISException(message, error_code=code, details=details)
        r._is_ok = False
        return r
    
    def is_ok(self) -> bool:
        return self._is_ok
    
    def is_err(self) -> bool:
        return not self._is_ok
    
    def unwrap(self) -> Any:
        """Get value or raise error."""
        if self._is_ok:
            return self._value
        raise self._error
    
    def unwrap_or(self, default: Any) -> Any:
        """Get value or return default."""
        return self._value if self._is_ok else default
    
    def unwrap_or_else(self, f: callable) -> Any:
        """Get value or compute from function."""
        return self._value if self._is_ok else f(self._error)
    
    def map(self, f: callable) -> 'Result':
        """Transform value if ok."""
        if self._is_ok:
            return Result.ok(f(self._value))
        return self
    
    def expect(self, message: str) -> Any:
        """Get value or panic with message."""
        if self._is_ok:
            return self._value
        raise RuntimeError(f"{message}: {self._error}")
