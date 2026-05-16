class AntigravityError(Exception):
    """Base exception for all Antigravity errors."""
    pass

class ModNotFoundError(AntigravityError):
    """Raised when a requested mod cannot be found."""
    pass

class VersionNotFoundError(AntigravityError):
    """Raised when no matching version could be found for the given criteria."""
    pass

class ApiError(AntigravityError):
    """Raised when the API returns an error or is unreachable."""
    pass
