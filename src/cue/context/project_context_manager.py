import logging
from typing import Dict
from pathlib import Path
from typing_extensions import Optional

logger = logging.getLogger(__name__)


class ProjectContextManager:
    def load_project_context(self, path: Optional[str]) -> Optional[Dict]:
        """Load project context."""
        if path is None:
            return None
        try:
            context_path = Path(path)
            if context_path.exists():
                with open(context_path) as f:
                    context = f.read()
                    return {
                        "role": "user",
                        "content": f"Project context path: {context_path} <project_context>\n{context}\n</project_context>",
                    }
            else:
                logger.info(f"No project context provided, {context_path}")
        except Exception as e:
            logger.error(f"Failed to load project context: {e}")
        return None
