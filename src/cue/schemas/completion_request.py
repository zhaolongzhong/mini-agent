from typing import Dict, List, Optional

from pydantic import Field, BaseModel

from .message import Author
from .run_metadata import RunMetadata


class CompletionRequest(BaseModel):
    author: Optional[Author] = Field(default=None, description="Author")
    messages: list[Dict]
    model: str = "gpt-4o"
    max_tokens: int = Field(default=4096, ge=1, description="The maximum number of tokens to generate.")
    temperature: float = Field(default=0.8, ge=0, le=2, description="The sampling temperature for generation.")
    response_format_type: Optional[str] = "text"  # `json_object`
    response_format: Optional[Dict] = {"type": "text"}
    tool_json: Optional[List[Dict]] = None  # tool json defintion
    tool_choice: Optional[str] = "auto"
    parallel_tool_calls: Optional[bool] = Field(
        default=True,
        description="Whether to enable parallel function calling during tool use. Defaults to true.",
    )
    metadata: Optional[RunMetadata] = None
    system_prompt_suffix: Optional[str] = ""
    system_context: Optional[str] = ""
    enable_prompt_caching: Optional[bool] = True
