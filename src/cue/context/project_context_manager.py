import logging
from pathlib import Path
from typing_extensions import Optional

from ..utils.token_counter import TokenCounter

logger = logging.getLogger(__name__)


class ProjectContextManager:
    def __init__(self, path: Optional[str]):
        self.path = path
        self.pre_context: Optional[str] = None
        self.project_context: Optional[str] = None
        self.token_counter = TokenCounter()
        self.message_params: Optional[dict] = None

    def update_context(self) -> None:
        """Load project context."""
        if self.path is None:
            logger.debug("No project context path provided")
            return None
        try:
            context_path = Path(self.path)
            if context_path.exists():
                with open(context_path) as f:
                    self.pre_context = self.project_context
                    self.project_context = f.read()
                    self.update_params()

            else:
                logger.info(f"No project context provided, {context_path}")
        except Exception as e:
            logger.error(f"Failed to load project context: {e}")
        return None

    def update_params(self) -> Optional[dict]:
        tokens = self.token_counter.count_token(self.project_context)
        token_context = f"<project_context_token>{tokens}</project_context_token>"
        if not self.pre_context and not self.project_context:
            return None

        if self.pre_context and not self.project_context:
            self.message_params = {
                "role": "user",
                "content": f"Project context path: {self.path} <project_context></project_context>, the content in the file has been overwritten with empty, if this is not expected please revert or update, here is previous context: <pre_project_context>{self.pre_context}</pre_project_context> {token_context}",
            }
            self.pre_context = None
        else:
            self.message_params = {
                "role": "user",
                "content": f"Project context path: {self.path} <project_context>\n{self.project_context}\n</project_context>{token_context}",
            }
            self.pre_context = self.message_params

    def get_params(self) -> Optional[dict]:
        return self.message_params
