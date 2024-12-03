from typing import List, Optional
from pydantic import BaseModel, Field


class PersonalityConfig(BaseModel):
    """Configuration for agent personality and behavioral characteristics"""
    traits: List[str] = Field(
        default_factory=list,
        description="List of personality traits that define the agent's behavior"
    )
    learning_style: Optional[str] = Field(
        None,
        description="The agent's preferred approach to learning and processing information"
    )
    communication_style: Optional[str] = Field(
        None,
        description="The agent's preferred style of communication"
    )
    role_traits: Optional[List[str]] = Field(
        default_factory=list,
        description="Traits specific to the agent's role or specialization"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "traits": ["analytical", "curious", "systematic"],
                "learning_style": "active",
                "communication_style": "precise",
                "role_traits": ["detail-oriented", "methodical"]
            }
        }