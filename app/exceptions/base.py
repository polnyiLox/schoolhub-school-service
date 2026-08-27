class AppError(Exception):
    """Base class for errors that the API layer may safely expose."""

    default_detail = "Application error"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.default_detail
        super().__init__(self.detail)


class NotFoundError(AppError):
    pass


class AccessDeniedError(AppError):
    pass


class ConflictError(AppError):
    pass


class ValidationError(AppError):
    pass
