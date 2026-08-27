class AppError(Exception):
    """Base class for errors that the API layer may safely expose."""

    status_code = 500
    default_detail = "Application error"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.default_detail
        super().__init__(self.detail)


class NotFoundError(AppError):
    status_code = 404


class AccessDeniedError(AppError):
    status_code = 403


class ConflictError(AppError):
    status_code = 409


class ValidationError(AppError):
    status_code = 422
