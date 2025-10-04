from fastapi import HTTPException, status

class AppException(HTTPException):
    def __init__(self, message: str, code: str = "APP_ERROR", status_code: int = status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(status_code=status_code, detail=message)

class ValidationException(AppException):
    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )

class AuthenticationException(AppException):
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            code="AUTH_ERROR",
            status_code=status.HTTP_401_UNAUTHORIZED
        )

class AuthorizationException(AppException):
    def __init__(self, message: str = "Access denied"):
        super().__init__(
            message=message,
            code="ACCESS_DENIED",
            status_code=status.HTTP_403_FORBIDDEN
        )

class NotFoundException(AppException):
    def __init__(self, resource: str = "Resource"):
        super().__init__(
            message=f"{resource} not found",
            code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND
        )

class ConflictException(AppException):
    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=status.HTTP_409_CONFLICT
        )

class PaymentException(AppException):
    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="PAYMENT_ERROR",
            status_code=status.HTTP_402_PAYMENT_REQUIRED
        )