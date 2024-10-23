import os
from typing import ClassVar, Literal

from pypdf import PdfReader

from .base import BaseTool


class ReadTool(BaseTool):
    """
    A tool that allows the agent to read content from file.
    """

    name: ClassVar[Literal["read_file"]] = "read_file"

    def __init__(self):
        self._function = self.read_file
        super().__init__()

    async def __call__(self, file_path: str, encoding: str = "utf-8", **kwargs):
        return await self.read_file(file_path, encoding)

    async def read_file(self, file_path: str, encoding: str = "utf-8") -> str:
        """Read and return the contents of a text or PDF file.

        Args:
            file_path (str): Path to the file to read.
            encoding (str, optional): File encoding. Defaults to 'utf-8'.

        Returns:
            str: File contents as string, or error message if file cannot be read.

        """
        if not os.path.isfile(file_path):
            return f"Error: The file {file_path} does not exist."

        try:
            if file_path.lower().endswith(".pdf"):
                reader = PdfReader(file_path)
                text = "".join(page.extract_text() for page in reader.pages)
            else:
                with open(file_path, encoding=encoding) as f:
                    text = f.read()
            original_length = len(text)
            max_lenth = 5000
            if original_length > max_lenth:
                visible_text = text[:max_lenth]
                visibility_percentage = (max_lenth / original_length) * 100
                visibility_info = f"\n\n[Truncated to {max_lenth} characters, visibility: {visibility_percentage:.2f}%]"
                return visible_text + visibility_info
            else:
                return text
        except Exception as error:
            return f"Error: {error}"
