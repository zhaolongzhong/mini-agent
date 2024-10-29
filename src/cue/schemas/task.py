from typing import Any, Optional
from datetime import datetime, timezone

from pydantic import Field, BaseModel


class Task(BaseModel):
    """
    Task: The basic unit of work. It can have subtasks (for complex tasks) or be a leaf task (for simple tasks).
    """

    id: Optional[str] = Field(default=None, description="Unique identifier for the task, e.g., task_01")
    description: Optional[str] = Field(default=None, description="Goal or main description of the task")
    status: Optional[str] = Field(default="pending", description="Current status: pending, in_progress, done")
    parent_id: Optional[str] = Field(default=None, description="ID of the parent task, if any")
    subtasks: Optional[list[str]] = Field(default=None, description="List of subtask IDs or descriptions")
    requirements: Optional[list[str]] = Field(default=None, description="List of task requirements")
    resources: Optional[list[str]] = Field(
        default=None, description="List of relevant resources (URLs, file paths, etc.)"
    )
    metadata: Optional[dict[str, Any]] = Field(default=None, description="Additional task-specific information")
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Timestamp of the last update in ISO 8601 format",
    )

    class ConfigDict:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "id": "task_01",
                "description": "Implement user authentication feature",
                "status": "in_progress",
                "parent_id": None,
                "subtasks": [
                    "Design database schema",
                    "Implement login endpoint",
                    "Add password hashing",
                ],
                "requirements": [
                    "Must support OAuth 2.0",
                    "Passwords must be at least 8 characters long",
                ],
                "resources": ["https://auth0.com/docs/", "https://oauth.net/2/"],
                "metadata": {
                    "working_directory": "/home/user/projects/auth_system",
                    "estimated_hours": 20,
                    "priority": "high",
                },
            }
        }
