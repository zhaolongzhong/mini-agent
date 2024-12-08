"""Context management tool for handling system, project and environment contexts."""

import json
import enum
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Literal, ClassVar

from pydantic import BaseModel, Field

from cue.tools import BaseTool


class ContextType(str, enum.Enum):
    """Types of context that can be managed."""
    SYSTEM = "system"
    PROJECT = "project"
    ENV = "env"


class ContextCommand(str, enum.Enum):
    """Available context operations."""
    VIEW = "view"      # View current context
    UPDATE = "update"  # Update existing context
    QUERY = "query"    # Query specific context info
    CREATE = "create"  # Create new context entry


class ContextSchema(BaseModel):
    """Base schema for context entries."""
    version: str = Field(default="0.1.0")
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    content: Dict[str, Any] = Field(default_factory=dict)


class ContextRequest(BaseModel):
    """Schema for context operation requests."""
    command: ContextCommand
    context_type: ContextType
    path: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    query: Optional[str] = None


class ContextTool(BaseTool):
    """Tool for managing system and project context awareness."""
    
    name: ClassVar[Literal["context"]] = "context"
    base_path: ClassVar[Path] = Path("/Users/zz/atlas/context")
    
    def __init__(self) -> None:
        """Initialize context tool with base configuration."""
        super().__init__()
        self.contexts: Dict[str, Dict[str, Any]] = {}
        self._load_contexts()

    def _load_contexts(self) -> None:
        """Load all context files into memory."""
        for context_type in ContextType:
            type_path = self.base_path / context_type.value
            if not type_path.exists():
                continue
                
            self.contexts[context_type.value] = {}
            for file in type_path.glob("*.json"):
                try:
                    with open(file, "r") as f:
                        self.contexts[context_type.value][file.stem] = json.load(f)
                except Exception as e:
                    print(f"Error loading {file}: {e}")

    def _save_context(self, context_type: ContextType, name: str) -> None:
        """Save a specific context back to file."""
        if context_type.value not in self.contexts:
            return
            
        if name not in self.contexts[context_type.value]:
            return
            
        file_path = self.base_path / context_type.value / f"{name}.json"
        with open(file_path, "w") as f:
            json.dump(
                self.contexts[context_type.value][name],
                f,
                indent=4,
                default=str
            )

    def view(self, context_type: ContextType, path: Optional[str] = None) -> Dict[str, Any]:
        """View context content, optionally at a specific path."""
        if context_type.value not in self.contexts:
            return {}
            
        if not path:
            return self.contexts[context_type.value]
            
        parts = path.split("/")
        current = self.contexts[context_type.value]
        for part in parts:
            if part not in current:
                return {}
            current = current[part]
            
        return current

    def update(
        self,
        context_type: ContextType,
        path: str,
        content: Dict[str, Any]
    ) -> bool:
        """Update context at specified path."""
        if context_type.value not in self.contexts:
            return False
            
        parts = path.split("/")
        name = parts[0]
        if name not in self.contexts[context_type.value]:
            return False
            
        current = self.contexts[context_type.value][name]
        for part in parts[1:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
            
        current[parts[-1]] = content
        self._save_context(context_type, name)
        return True

    def query(
        self,
        context_type: ContextType,
        query: str
    ) -> List[Dict[str, Any]]:
        """Query contexts using simple path expressions."""
        if context_type.value not in self.contexts:
            return []
            
        results = []
        for name, content in self.contexts[context_type.value].items():
            if query in json.dumps(content):
                results.append({name: content})
                
        return results

    def create(
        self,
        context_type: ContextType,
        path: str,
        content: Dict[str, Any]
    ) -> bool:
        """Create new context entry."""
        if context_type.value not in self.contexts:
            return False
            
        parts = path.split("/")
        name = parts[0]
        
        if name in self.contexts[context_type.value]:
            return False
            
        self.contexts[context_type.value][name] = content
        self._save_context(context_type, name)
        return True

    async def __call__(
        self,
        command: ContextCommand,
        context_type: ContextType,
        path: Optional[str] = None,
        content: Optional[Dict[str, Any]] = None,
        query: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute context operation based on command."""
        if command == ContextCommand.VIEW:
            return self.view(context_type, path)
            
        elif command == ContextCommand.UPDATE:
            if not path or not content:
                return {"error": "Path and content required for update"}
            success = self.update(context_type, path, content)
            return {"success": success}
            
        elif command == ContextCommand.QUERY:
            if not query:
                return {"error": "Query required for search"}
            results = self.query(context_type, query)
            return {"results": results}
            
        elif command == ContextCommand.CREATE:
            if not path or not content:
                return {"error": "Path and content required for create"}
            success = self.create(context_type, path, content)
            return {"success": success}
            
        return {"error": "Invalid command"}