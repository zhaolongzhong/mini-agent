import os
from typing import Literal, ClassVar

from .base import BaseTool


class WriteTool(BaseTool):
    """A tool that allows the agent to write content to file."""

    name: ClassVar[Literal["write_to_file"]] = "write_to_file"

    def __init__(self):
        self._function = self.write_to_file
        super().__init__()

    async def __call__(self, file_path: str, content: str, encoding: str = "utf-8"):
        return await self.write_to_file(file_path, content, encoding)

    async def write_to_file(self, file_path: str, content: str, encoding: str = "utf-8") -> str:
        """Write string content to a file.

        Args:
            file_path (str): Path where the file will be written.
            content (str): Content to write to the file.
            encoding (str, optional): File encoding. Defaults to 'utf-8'.

        Returns:
            str: Success message or error message if write fails.

        """
        try:
            # Creating the directory if it does not exist
            directory = os.path.dirname(file_path)
            if directory:
                os.makedirs(directory, exist_ok=True)

            # Writing text to the file
            with open(file_path, "w", encoding=encoding) as f:
                f.write(content)
            return "File written successfully."
        except Exception as error:
            return f"Error: {error}"
