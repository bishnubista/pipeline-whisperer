"""
Retry logic with exponential backoff and circuit breaker pattern
"""
import asyncio
import time
from functools import wraps
from typing import Any, Callable, Optional, Type, Tuple

from app.utils.logger import get_logger

logger = get_logger(__name__)


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_failure: Optional[Callable] = None,
):
    """
    Decorator for retrying functions with exponential backoff

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential_base: Base for exponential backoff calculation
        exceptions: Tuple of exceptions to catch and retry
        on_failure: Optional callback function to call on final failure
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.error(
                            f"Function {func.__name__} failed after {max_retries} retries",
                            extra={
                                "function": func.__name__,
                                "attempts": max_retries + 1,
                                "error": str(e),
                            }
                        )
                        if on_failure:
                            on_failure(e)
                        raise

                    logger.warning(
                        f"Function {func.__name__} failed, retrying in {delay}s (attempt {attempt + 1}/{max_retries})",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt + 1,
                            "delay": delay,
                            "error": str(e),
                        }
                    )

                    await asyncio.sleep(delay)
                    delay = min(delay * exponential_base, max_delay)

            raise last_exception

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.error(
                            f"Function {func.__name__} failed after {max_retries} retries",
                            extra={
                                "function": func.__name__,
                                "attempts": max_retries + 1,
                                "error": str(e),
                            }
                        )
                        if on_failure:
                            on_failure(e)
                        raise

                    logger.warning(
                        f"Function {func.__name__} failed, retrying in {delay}s (attempt {attempt + 1}/{max_retries})",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt + 1,
                            "delay": delay,
                            "error": str(e),
                        }
                    )

                    time.sleep(delay)
                    delay = min(delay * exponential_base, max_delay)

            raise last_exception

        # Return appropriate wrapper based on whether function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern implementation
    Prevents cascading failures by failing fast when a service is down
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half_open

    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            if self.state == "open":
                if time.time() - self.last_failure_time >= self.recovery_timeout:
                    self.state = "half_open"
                    logger.info(f"Circuit breaker for {func.__name__} entering half-open state")
                else:
                    raise Exception(f"Circuit breaker is open for {func.__name__}")

            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as e:
                self._on_failure()
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            if self.state == "open":
                if time.time() - self.last_failure_time >= self.recovery_timeout:
                    self.state = "half_open"
                    logger.info(f"Circuit breaker for {func.__name__} entering half-open state")
                else:
                    raise Exception(f"Circuit breaker is open for {func.__name__}")

            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as e:
                self._on_failure()
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    def _on_success(self):
        """Reset circuit breaker on success"""
        self.failure_count = 0
        if self.state == "half_open":
            self.state = "closed"
            logger.info("Circuit breaker closed after successful call")

    def _on_failure(self):
        """Handle failure and potentially open circuit"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(
                f"Circuit breaker opened after {self.failure_count} failures",
                extra={"failure_count": self.failure_count}
            )
