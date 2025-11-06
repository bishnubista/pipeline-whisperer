"""
Custom exception hierarchy for Pipeline Whisperer
Provides structured error handling with proper HTTP status codes
"""
from typing import Any, Dict, Optional


class PipelineWhispererException(Exception):
    """Base exception for all Pipeline Whisperer errors"""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(PipelineWhispererException):
    """Raised when input validation fails"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=400, details=details)


class AuthenticationError(PipelineWhispererException):
    """Raised when authentication fails"""

    def __init__(self, message: str = "Authentication required", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=401, details=details)


class AuthorizationError(PipelineWhispererException):
    """Raised when authorization fails"""

    def __init__(self, message: str = "Insufficient permissions", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=403, details=details)


class NotFoundError(PipelineWhispererException):
    """Raised when a resource is not found"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=404, details=details)


class ConflictError(PipelineWhispererException):
    """Raised when there's a conflict with existing resources"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=409, details=details)


class RateLimitError(PipelineWhispererException):
    """Raised when rate limit is exceeded"""

    def __init__(self, message: str = "Rate limit exceeded", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=429, details=details)


class ExternalServiceError(PipelineWhispererException):
    """Raised when an external service fails"""

    def __init__(self, service_name: str, message: str, details: Optional[Dict[str, Any]] = None):
        self.service_name = service_name
        details = details or {}
        details["service"] = service_name
        super().__init__(f"{service_name} error: {message}", status_code=503, details=details)


class OpenAIServiceError(ExternalServiceError):
    """Raised when OpenAI service fails"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__("OpenAI", message, details)


class LightfieldServiceError(ExternalServiceError):
    """Raised when Lightfield service fails"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__("Lightfield", message, details)


class TruefoundryServiceError(ExternalServiceError):
    """Raised when Truefoundry service fails"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__("Truefoundry", message, details)


class KafkaServiceError(ExternalServiceError):
    """Raised when Kafka/Redpanda service fails"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__("Kafka", message, details)


class DatabaseError(PipelineWhispererException):
    """Raised when database operations fail"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(f"Database error: {message}", status_code=500, details=details)


class ConfigurationError(PipelineWhispererException):
    """Raised when configuration is invalid"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(f"Configuration error: {message}", status_code=500, details=details)
