from typing import Literal

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(..., max_length=10000)


class ChatRequest(BaseModel):
    model: str = Field(..., min_length=1, max_length=100)
    messages: list[Message] = Field(..., min_length=1)
    temperature: float | None = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=512, ge=1, le=32768)
    stream: bool | None = False
