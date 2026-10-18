"""Domain errors raised by the service layer; the API maps each one to an HTTP status."""


class DomainError(Exception):
    """Base class for expected business failures."""

    default_message = "The request could not be completed."

    def __init__(self, message: str | None = None):
        """Store a human-readable message."""
        self.message = message or self.default_message
        super().__init__(self.message)


class NotFoundError(DomainError):
    """A referenced resource does not exist."""

    default_message = "Resource not found."


class PermissionDeniedError(DomainError):
    """The caller is authenticated but not allowed to do this."""

    default_message = "You do not have permission to perform this action."


class ConflictError(DomainError):
    """The request conflicts with the current state (duplicate or overlap)."""

    default_message = "The request conflicts with the current state."


class BusinessRuleError(DomainError):
    """The request is well-formed but breaks a business rule."""

    default_message = "The request breaks a business rule."


class InvalidCredentialsError(DomainError):
    """Login credentials or a refresh token are not valid."""

    default_message = "Invalid credentials."
