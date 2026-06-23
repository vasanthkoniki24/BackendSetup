from fastapi import status


class AppException(Exception):
    def __init__(self, status_code: int, message: str, detail: str = None):
        self.status_code = status_code
        self.message = message
        self.detail = detail
        super()._init_(message)


class NotFoundError(AppException):
    def __init__(self, resource: str = "Resource"):
        super()._init_(status.HTTP_404_NOT_FOUND, f"{resource} not found")


class ConflictError(AppException):
    def __init__(self, message: str = "Resource already exists"):
        super()._init_(status.HTTP_409_CONFLICT, message)


class UnauthorizedError(AppException):
    def __init__(self, message: str = "Unauthorized"):
        super()._init_(status.HTTP_401_UNAUTHORIZED, message)


class ForbiddenError(AppException):
    def __init__(self, message: str = "Forbidden"):
        super()._init_(status.HTTP_403_FORBIDDEN, message)


class ValidationError(AppException):
    def __init__(self, message: str = "Validation failed"):
        super()._init_(status.HTTP_422_UNPROCESSABLE_ENTITY, message)