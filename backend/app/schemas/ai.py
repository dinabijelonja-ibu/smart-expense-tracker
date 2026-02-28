from pydantic import BaseModel, Field


class AIChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class AIChatResponse(BaseModel):
    response: str


class RebuildEmbeddingsRequest(BaseModel):
    month: str | None = Field(default=None, description="YYYY-MM format; defaults to current month")


class RebuildEmbeddingsResponse(BaseModel):
    id: int
    status: str
    content: str
