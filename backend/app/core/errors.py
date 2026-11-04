"""One error envelope, every endpoint. See docs/contracts.md section 3."""
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

    def envelope(self) -> dict:
        return {"success": False, "data": None,
                "error": {"code": self.code, "message": self.message, "field": self.field}}

def ok(data):
    return {"success": True, "data": data, "error": None}
