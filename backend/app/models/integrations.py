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


class ResearchEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    query: str = Field(min_length=1)
    title: str = Field(min_length=1)
    url: HttpUrl
    excerpt: str = Field(min_length=1, max_length=1000)
    relevance: float = Field(ge=0, le=1)
    explanation: str = Field(min_length=1)
