from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class TraveliaException(Exception):
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(TraveliaException):
    def __init__(self, resource: str):
        super().__init__(f"{resource} not found", status.HTTP_404_NOT_FOUND)


class UnauthorizedError(TraveliaException):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED)


class ForbiddenError(TraveliaException):
    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, status.HTTP_403_FORBIDDEN)


class ConflictError(TraveliaException):
    def __init__(self, message: str):
        super().__init__(message, status.HTTP_409_CONFLICT)


class BusinessRuleError(TraveliaException):
    def __init__(self, message: str):
        super().__init__(message, status.HTTP_422_UNPROCESSABLE_ENTITY)


class PaymentGatewayError(TraveliaException):
    def __init__(self, message: str = "Payment gateway error"):
        super().__init__(message, status.HTTP_502_BAD_GATEWAY)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(TraveliaException)
    async def travelia_exception_handler(request: Request, exc: TraveliaException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message},
        )
