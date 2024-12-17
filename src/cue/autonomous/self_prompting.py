"""
Self-Prompting System for Atlas

This module implements the self-prompting mechanism that enables Atlas to:
- Generate contextually appropriate prompts
- Select and prioritize actions
- Maintain conversation coherence in autonomous mode
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

class PromptTemplate:
    """Represents a prompt template for autonomous actions"""
    def __init__(self, template: str, required_context: List[str], priority: int = 1):
        self.template = template
        self.required_context = required_context
        self.priority = priority
        self.last_used = None

    def format(self, context: Dict[str, Any]) -> Optional[str]:
        """Format template with given context if all required fields are present"""
        if all(key in context for key in self.required_context):
            self.last_used = datetime.now()
            return self.template.format(**context)
        return None

class SelfPromptManager:
    """Manages self-prompting capabilities"""
    def __init__(self):
        self.prompt_templates: Dict[str, PromptTemplate] = {}
        self.action_context: Dict[str, Any] = {}
        self._initialize_default_templates()

    def _initialize_default_templates(self):
        """Set up default prompt templates"""
        # Health check template
        self.add_template(
            "health_check",
            PromptTemplate(
                template="Perform system health check:\n"
                        "1. Check memory usage and optimization\n"
                        "2. Verify tool availability\n"
                        "3. Review recent error patterns\n"
                        "4. Generate health report\n"
                        "\nContext: {context}",
                required_context=["context"],
                priority=2
            )
        )

        # Memory optimization template
        self.add_template(
            "memory_optimize",
            PromptTemplate(
                template="Optimize memory system:\n"
                        "1. Analyze memory usage patterns\n"
                        "2. Identify optimization opportunities\n"
                        "3. Apply optimization strategies\n"
                        "4. Verify improvements\n"
                        "\nTarget: {target}\nScope: {scope}",
                required_context=["target", "scope"],
                priority=1
            )
        )

    def add_template(self, name: str, template: PromptTemplate):
        """Add a new prompt template"""
        self.prompt_templates[name] = template

    def update_context(self, context: Dict[str, Any]):
        """Update the action context"""
        self.action_context.update(context)

    def generate_prompt(self, template_name: str, additional_context: Dict[str, Any]) -> Optional[str]:
        """Generate a prompt using the named template and combined context"""
        template = self.prompt_templates.get(template_name)
        if not template:
            return None

        # Combine global and additional context
        context = {**self.action_context, **additional_context}
        return template.format(context)

    def get_template_status(self) -> Dict[str, Any]:
        """Get current status of prompt templates"""
        return {
            "available_templates": list(self.prompt_templates.keys()),
            "global_context_keys": list(self.action_context.keys()),
            "template_usage": {
                name: template.last_used
                for name, template in self.prompt_templates.items()
            }
        }