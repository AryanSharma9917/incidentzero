from typing import Literal
from pydantic import BaseModel


class RuntimeInfo(BaseModel):
    execution_mode: Literal["kubernetes", "simulation"]
    runs_enabled: bool
    access_code_required: bool
    provider_configured: bool
    storage_ephemeral: bool
    daily_run_limit: int
