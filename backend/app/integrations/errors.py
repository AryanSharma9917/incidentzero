class IntegrationError(RuntimeError):
    """Base error for a failed external integration call."""


class IntegrationNotConfiguredError(IntegrationError):
    """Raised when an integration is used without its required credentials."""


class IntegrationResponseError(IntegrationError):
    """Raised when an upstream response is unsuccessful or malformed."""
