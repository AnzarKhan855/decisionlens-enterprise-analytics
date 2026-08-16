import time
import functools
import threading
import logging
from typing import Any, Callable, Dict, Optional, Type, Tuple
from datetime import datetime, timezone

from app.observability.structured_logger import get_logger, log_with_context

logger = get_logger(__name__)


class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        success_threshold: int = 3,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self._state = "CLOSED"
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = threading.Lock()

    def _is_open(self) -> bool:
        if self._state == "OPEN":
            if self._last_failure_time and (time.time() - self._last_failure_time) >= self.recovery_timeout:
                self._state = "HALF_OPEN"
                self._success_count = 0
                return False
            return True
        return False

    def record_success(self) -> None:
        with self._lock:
            if self._state == "HALF_OPEN":
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    self._state = "CLOSED"
                    self._failure_count = 0
                    logger.info("[CircuitBreaker] %s recovered and closed", self.name)
            else:
                self._failure_count = 0

    def record_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._failure_count >= self.failure_threshold:
                self._state = "OPEN"
                logger.warning("[CircuitBreaker] %s opened after %d failures", self.name, self._failure_count)

    def get_state(self) -> str:
        return self._state


_circuit_breakers: Dict[str, CircuitBreaker] = {}
_cb_lock = threading.Lock()


def get_circuit_breaker(name: str, **kwargs) -> CircuitBreaker:
    with _cb_lock:
        if name not in _circuit_breakers:
            _circuit_breakers[name] = CircuitBreaker(name, **kwargs)
        return _circuit_breakers[name]


def with_retry(
    max_attempts: int = 3,
    backoff_factor: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    circuit_breaker_name: Optional[str] = None,
    fallback: Optional[Callable[[], Any]] = None,
) -> Callable:
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            cb = get_circuit_breaker(circuit_breaker_name or func.__name__) if circuit_breaker_name else None

            if cb and cb._is_open():
                logger.warning("[Retry] Circuit breaker %s is open, skipping %s", cb.name, func.__name__)
                if fallback:
                    return fallback()
                raise Exception(f"Circuit breaker {cb.name} is open")

            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    result = func(*args, **kwargs)
                    if cb:
                        cb.record_success()
                    return result
                except exceptions as exc:
                    last_exception = exc
                    exc_str = str(exc)
                    if any(unretriable in exc_str for unretriable in ("Binder Error", "Catalog Error", "Parser Error", "not found in FROM clause")):
                        log_with_context(
                            logging.WARNING,
                            f"[Retry] Non-retriable SQL error in {func.__name__}: {exc_str}",
                            engine=func.__name__,
                        )
                        if fallback:
                            return fallback()
                        raise exc

                    if cb:
                        cb.record_failure()
                    log_with_context(
                        logging.WARNING,
                        f"[Retry] Attempt {attempt}/{max_attempts} failed for {func.__name__}: {exc}",
                        engine=func.__name__,
                    )
                    if attempt < max_attempts:
                        sleep_time = backoff_factor * (2 ** (attempt - 1))
                        time.sleep(sleep_time)

            if fallback:
                log_with_context(
                    logging.WARNING,
                    f"[Retry] All {max_attempts} attempts failed for {func.__name__}, using fallback",
                    engine=func.__name__,
                )
                return fallback()

            raise last_exception  # type: ignore

        return wrapper
    return decorator


def fallback_empty_list() -> list:
    return []


def fallback_empty_dict() -> dict:
    return {}


def fallback_none() -> None:
    return None
