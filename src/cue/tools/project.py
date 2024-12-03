"""Project management tool for tracking and managing tasks."""

import json
import logging
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .base import BaseTool

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task status enum."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"


class TaskPriority(str, Enum):
    """Task priority enum."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Task(BaseModel):
    """Task model."""

    id: str = Field(..., description="Unique task identifier")
    title: str = Field(..., description="Task title")
    description: Optional[str] = Field(None, description="Task description")
    status: TaskStatus = Field(default=TaskStatus.TODO, description="Task status")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Task priority")
    tags: List[str] = Field(default_factory=list, description="Task tags")
    dependencies: List[str] = Field(default_factory=list, description="IDs of tasks this task depends on")
    created_at: str = Field(..., description="Task creation timestamp")
    updated_at: str = Field(..., description="Task last update timestamp")
    assignee: Optional[str] = Field(None, description="Task assignee")
    due_date: Optional[str] = Field(None, description="Task due date")


class ProjectTool(BaseTool):
    """Tool for managing project tasks."""

    name = "project"
    description = (
        "Project management tool for managing tasks and tracking progress.\n"
        "Available commands:\n"
        "- list: List tasks with optional filters\n"
        "- view: View task details\n"
        "- create: Create a new task\n"
        "- update: Update task status or details\n"
        "- delete: Delete a task\n"
        "- search: Search tasks by title, description, or tags\n"
    )

    def __init__(self):
        """Initialize project tool."""
        super().__init__()
        self.tasks: Dict[str, Task] = {}

    def _handle_tool_call(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool call with given arguments."""
        command = args.get("command", "")
        if not command:
            raise ToolCallError("Command is required")

        handlers = {
            "list": self._handle_list,
            "view": self._handle_view,
            "create": self._handle_create,
            "update": self._handle_update,
            "delete": self._handle_delete,
            "search": self._handle_search,
        }

        handler = handlers.get(command)
        if not handler:
            raise ToolCallError(f"Unknown command: {command}")

        return handler(args)

    def _handle_list(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle list command."""
        status = args.get("status")
        priority = args.get("priority")
        assignee = args.get("assignee")
        tags = args.get("tags", [])

        tasks = self.tasks.values()
        if status:
            tasks = [t for t in tasks if t.status == status]
        if priority:
            tasks = [t for t in tasks if t.priority == priority]
        if assignee:
            tasks = [t for t in tasks if t.assignee == assignee]
        if tags:
            tasks = [t for t in tasks if any(tag in t.tags for tag in tags)]

        return {"tasks": [t.dict() for t in tasks]}

    def _handle_view(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle view command."""
        task_id = args.get("task_id")
        if not task_id:
            raise ToolCallError("task_id is required")

        task = self.tasks.get(task_id)
        if not task:
            raise ToolCallError(f"Task not found: {task_id}")

        return {"task": task.dict()}

    def _handle_create(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle create command."""
        # Placeholder - would normally generate ID and timestamps
        task = Task(**args)
        self.tasks[task.id] = task
        return {"task": task.dict()}

    def _handle_update(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle update command."""
        task_id = args.pop("task_id", None)
        if not task_id:
            raise ToolCallError("task_id is required")

        task = self.tasks.get(task_id)
        if not task:
            raise ToolCallError(f"Task not found: {task_id}")

        # Update task fields
        task_dict = task.dict()
        task_dict.update(args)
        updated_task = Task(**task_dict)
        self.tasks[task_id] = updated_task

        return {"task": updated_task.dict()}

    def _handle_delete(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle delete command."""
        task_id = args.get("task_id")
        if not task_id:
            raise ToolCallError("task_id is required")

        if task_id not in self.tasks:
            raise ToolCallError(f"Task not found: {task_id}")

        task = self.tasks.pop(task_id)
        return {"task": task.dict()}

    def _handle_search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle search command."""
        query = args.get("query", "").lower()
        if not query:
            raise ToolCallError("query is required")

        matching_tasks = []
        for task in self.tasks.values():
            if (query in task.title.lower() or
                (task.description and query in task.description.lower()) or
                any(query in tag.lower() for tag in task.tags)):
                matching_tasks.append(task)

        return {"tasks": [t.dict() for t in matching_tasks]}