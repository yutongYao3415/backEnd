from typing import Any, Optional
from pydantic import BaseModel

class ApiResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    message: Optional[str] = None

def resp_success(data: Any = None, message: str = "Success") -> dict:
    return {"success": True, "data": data, "message": message}

def resp_error(message: str = "Error", data: Any = None) -> dict:
    return {"success": False, "data": data, "message": message}