from pydantic import BaseModel


class GatewayMeta(BaseModel):
    provider_used: str
    model_used: str
    latency_ms: int = 0
    request_id: str
    fallback_triggered: bool = False
    providers_tried: list[str] = []
    estimated_cost_usd: float = 0.0


class UsageInfo(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class MessageOutput(BaseModel):
    role: str
    content: str


class Choice(BaseModel):
    index: int
    message: MessageOutput
    finish_reason: str


class ChatResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[Choice]
    usage: UsageInfo
    x_gateway: GatewayMeta


class DeltaMessage(BaseModel):
    role: str | None = None
    content: str | None = None


class ChunkChoice(BaseModel):
    index: int = 0
    delta: DeltaMessage
    finish_reason: str | None = None


class ChatCompletionChunk(BaseModel):
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: list[ChunkChoice]
    x_gateway: GatewayMeta | None = None
