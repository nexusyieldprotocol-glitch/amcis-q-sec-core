"""
AMCIS Error Handling Utilities
==============================

Optimized utilities for common error handling patterns.
Reduces boilerplate and improves performance.
"""

import functools
import time
from typing import Any, Callable, Optional, TypeVar, Union, List
from contextlib import contextmanager
import structlog

from .amcis_exceptions import (
    AMCISException, ErrorCode, ErrorContext, Result,
    raise_invalid_argument, raise_not_found, raise_permission_denied, raise_timeout
)

T = TypeVar('T')

# Pre-created logger for performance
_error_logger = structlog.get_logger("amcis.errors")


class SafeCall:
    """
    Utility for safe function calls with automatic error handling.
    Eliminates repetitive try/except blocks.
    """
    
    __slots__ = ('default', 'error_code', 'log_errors', 'reraise')
    
    def __init__(
        self,
        default: Any = None,
        error_code: ErrorCode = ErrorCode.OPERATION_FAILED,
        log_errors: bool = True,
        reraise: bool = False
    ):
        self.default = default
        self.error_code = error_code
        self.log_errors = log_errors
        self.reraise = reraise
    
    def __call__(self, func: Callable[..., T], *args, **kwargs) -> Union[T, Any]:
        """Call function with error handling."""
        try:
            return func(*args, **kwargs)
        except AMCISException:
            if self.reraise:
                raise
            return self.default
        except Exception as e:
            if self.log_errors:
                _error_logger.error(
                    "safe_call_failed",
                    function=func.__name__,
                    error=str(e),
                    error_type=type(e).__name__
                )
            if self.reraise:
                raise AMCISException(
                    str(e),
                    error_code=self.error_code,
                    details={'function': func.__name__}
                ) from e
            return self.default


class RetryPolicy:
    """
    Configurable retry policy with exponential backoff.
    More efficient than manual retry loops.
    """
    
    __slots__ = ('max_retries', 'base_delay', 'max_delay', 'retryable_errors')
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 0.1,
        max_delay: float = 5.0,
        retryable_errors: Optional[tuple] = None
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.retryable_errors = retryable_errors or (AMCISException,)
    
    def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with retry logic."""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except self.retryable_errors as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    time.sleep(delay)
        
        raise last_error or AMCISException("Max retries exceeded")


# Optimized decorator factory
def safe_method(
    default: Any = None,
    error_code: ErrorCode = ErrorCode.OPERATION_FAILED,
    log: bool = True
):
    """Decorator for safe method execution."""
    def decorator(func: Callable[..., T]) -> Callable[..., Union[T, Any]]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Union[T, Any]:
            try:
                return func(*args, **kwargs)
            except AMCISException:
                raise
            except Exception as e:
                if log:
                    _error_logger.error(
                        "method_failed",
                        method=func.__name__,
                        error=str(e)
                    )
                raise AMCISException(
                    str(e),
                    error_code=error_code,
                    details={'method': func.__name__}
                ) from e
        return wrapper
    return decorator


def retry(
    max_retries: int = 3,
    delay: float = 0.1,
    exceptions: tuple = (Exception,)
):
    """Decorator for retry logic."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        time.sleep(delay * (2 ** attempt))
            raise last_error
        return wrapper
    return decorator


# Fast path validation functions (avoid exception creation for common cases)

def validate_not_none(value: Any, name: str) -> None:
    """Fast validation that value is not None."""
    if value is None:
        raise_invalid_argument(name, "cannot be None")


def validate_not_empty(value: Union[str, List, dict], name: str) -> None:
    """Fast validation that value is not empty."""
    if not value:
        raise_invalid_argument(name, "cannot be empty")


def validate_type(value: Any, expected_type: type, name: str) -> None:
    """Fast validation of type."""
    if not isinstance(value, expected_type):
        raise_invalid_argument(
            name,
            f"expected {expected_type.__name__}, got {type(value).__name__}"
        )


def validate_range(value: Union[int, float], min_val: Union[int, float], 
                   max_val: Union[int, float], name: str) -> None:
    """Fast validation of numeric range."""
    if not min_val <= value <= max_val:
        raise_invalid_argument(
            name,
            f"must be between {min_val} and {max_val}, got {value}"
        )


# Context managers for resource management

@contextmanager
def timing_context(operation: str, threshold_ms: float = 1000.0):
    """Context manager for timing operations with slow operation warnings."""
    start = time.perf_counter()
    logger = structlog.get_logger("amcis.perf")
    
    try:
        yield
    finally:
        elapsed = (time.perf_counter() - start) * 1000
        if elapsed > threshold_ms:
            logger.warning(
                "slow_operation",
                operation=operation,
                elapsed_ms=elapsed
            )


@contextmanager
def ignore_errors(*error_types: type, default: Any = None):
    """Context manager to ignore specific error types."""
    try:
        yield
    except error_types:
        pass


# Batch operation helpers

def batch_process(
    items: List[T],
    processor: Callable[[T], Any],
    error_code: ErrorCode = ErrorCode.OPERATION_FAILED,
    continue_on_error: bool = True
) -> Result:
    """
    Process items in batch with unified error handling.
    More efficient than manual loops with try/except.
    """
    results = []
    errors = []
    
    for item in items:
        try:
            results.append(processor(item))
        except Exception as e:
            if not continue_on_error:
                return Result.err(
                    f"Batch processing failed: {e}",
                    code=error_code,
                    item=str(item)
                )
            errors.append((item, str(e)))
    
    if errors and not results:
        return Result.err(
            f"All {len(errors)} batch items failed",
            code=error_code,
            errors=errors
        )
    
    return Result.ok({'results': results, 'errors': errors})


# Lazy error message formatting (avoid f-string overhead when not needed)

class LazyMessage:
    """Lazy error message formatting for performance."""
    
    __slots__ = ('template', 'args', 'kwargs')
    
    def __init__(self, template: str, *args, **kwargs):
        self.template = template
        self.args = args
        self.kwargs = kwargs
    
    def __str__(self) -> str:
        return self.template.format(*self.args, **self.kwargs)


def lazy_format(template: str, *args, **kwargs) -> LazyMessage:
    """Create lazy-formatted message."""
    return LazyMessage(template, *args, **kwargs)


# Import shortcuts for convenience
__all__ = [
    'SafeCall', 'RetryPolicy', 'safe_method', 'retry',
    'validate_not_none', 'validate_not_empty', 'validate_type', 'validate_range',
    'timing_context', 'ignore_errors', 'batch_process',
    'lazy_format', 'LazyMessage',
    'AMCISException', 'ErrorCode', 'ErrorContext', 'Result',
    'raise_invalid_argument', 'raise_not_found', 'raise_permission_denied', 'raise_timeout'
]
