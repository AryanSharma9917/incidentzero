from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class NebiusUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class NebiusCompletion(BaseModel):
    content: str
    model: str
    finish_reason: str | None = None
    usage: NebiusUsage = Field(default_factory=NebiusUsage)


class ResearchSource(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str
    url: HttpUrl
    content: str
    relevance: float = Field(ge=0, le=1)


class ResearchResults(BaseModel):
    query: str
    sources: list[ResearchSource]
    response_time: float | None = None
