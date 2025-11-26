"""Domain-level exception hierarchy."""


class DomainError(Exception):
    """Base exception for service-layer errors."""

    def __init__(self, message: str = "Domain error") -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    """Raised when a requested resource cannot be located."""


class ConflictError(DomainError):
    """Raised when a unique constraint or business rule is violated."""


class DuplicateHostnameError(ConflictError):
    """Raised when attempting to import a device with an existing hostname."""


class ForbiddenError(DomainError):
    """Raised when a user attempts an operation they are not allowed to perform."""


class ValidationError(DomainError):
    """Raised when input fails validation rules."""


class UnauthorizedError(DomainError):
    """Raised when authentication credentials are invalid."""
