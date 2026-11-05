"""One error envelope, every endpoint. See docs/contracts.md section 3.

Pattern: Factory Method - ``ApiError.not_found(...)`` etc. name the intent and
own the code, so call sites never repeat error-code strings."""
from dataclasses import dataclass

ERROR_CODES = {
    "VALIDATION_ERROR": 422,
    "UNAUTHORIZED": 401,
    "FORBIDDEN": 403,
    "NOT_FOUND": 404,
    "CONFLICT": 409,
    "SERVER_ERROR": 500,
}

@dataclass
class ApiError(Exception):
    code: str
    message: str
    field: str | None = None

    @property
    def status(self) -> int:
        return ERROR_CODES.get(self.code, 500)

    @classmethod
    def validation(cls, message: str, field: str | None = None) -> "ApiError":
        return cls("VALIDATION_ERROR", message, field)

    @classmethod
    def unauthorized(cls, message: str) -> "ApiError":
        return cls("UNAUTHORIZED", message)

    @classmethod
    def forbidden(cls, message: str) -> "ApiError":
        return cls("FORBIDDEN", message)

    @classmethod
    def not_found(cls, message: str) -> "ApiError":
        return cls("NOT_FOUND", message)

    @classmethod
    def conflict(cls, message: str) -> "ApiError":
        return cls("CONFLICT", message)

    def envelope(self) -> dict:
        return {"success": False, "data": None,
                "error": {"code": self.code, "message": self.message, "field": self.field}}

def ok(data):
    return {"success": True, "data": data, "error": None}
