from pydantic import BaseModel


class ActionResult(BaseModel):
    success: bool
    action: str
    message: str
    error: str | None = None
