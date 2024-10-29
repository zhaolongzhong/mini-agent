import base64
import json
import os
from dataclasses import dataclass
from typing import ClassVar, Literal, Optional

from cue.tools.utils.function_utils import get_definition_by_model

from .base import BaseTool


@dataclass(frozen=True)
class ToolResult:
    output: Optional[str] = None
    error: Optional[str] = None
    base64_image: Optional[str] = None
    system: Optional[str] = None


class ReadImageTool(BaseTool):
    """
    A tool that allows the agent to read image files and convert them to base64 format.
    Supports common image formats like PNG, JPEG, GIF, etc.
    """

    name: ClassVar[Literal["read_image"]] = "read_image"
    # https://docs.anthropic.com/en/docs/build-with-claude/vision#ensuring-image-quality
    # https://platform.openai.com/docs/guides/vision/can-i-use-gpt-4-to-generate-images
    SUPPORTED_FORMATS: ClassVar[tuple] = (".png", ".jpg", ".jpeg", ".webp")

    def __init__(self):
        self._function = self.read_image
        super().__init__()

    def to_json(self, model="", use_file_definition: bool = True) -> dict:
        """
        Generate the JSON schema for the tool.
        """
        defintion = {
            "type": "function",
            "function": {
                "name": "read_image",
                "description": "Read an image file and convert it to base64 format.",
                "parameters": {
                    "type": "object",
                    "properties": {"file_path": {"type": "string", "description": "The full path to the image file."}},
                    "required": ["file_path"],
                },
            },
        }
        return get_definition_by_model(defintion, model)

    async def __call__(self, file_path: str, **kwargs) -> ToolResult:
        return await self.read_image(file_path)

    def _get_media_type(self, file_extension: str) -> str:
        """
        Determine the media type based on file extension.
        """
        media_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
        }
        return media_types.get(file_extension.lower(), "application/octet-stream")

    async def read_image(self, file_path: str) -> ToolResult:
        """
        Read an image file and convert it to base64 format.

        Args:
            file_path (str): Full path to the image file.

        Returns:
            ToolResult: Contains the base64 encoded image or error information
        """
        if not os.path.isfile(file_path):
            return ToolResult(error=f"Error: The file {file_path} does not exist.")

        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension not in self.SUPPORTED_FORMATS:
            return ToolResult(
                error=f"Error: Unsupported file format. Supported formats are: {', '.join(self.SUPPORTED_FORMATS)}"
            )

        try:
            with open(file_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode("utf-8")

            return ToolResult(
                base64_image=base64_image,
                output=f"Successfully read image from {file_path}",
                system=f"Image type: {self._get_media_type(file_extension)}",
            )

        except Exception as error:
            return ToolResult(error=f"Error reading image file: {error}")

    async def get_image_info(self, file_path: str) -> ToolResult:
        """
        Get basic information about an image file.

        Args:
            file_path (str): Full path to the image file.

        Returns:
            ToolResult: Contains image information or error
        """
        try:
            file_size = os.path.getsize(file_path)
            file_extension = os.path.splitext(file_path)[1]
            info = {
                "file_name": os.path.basename(file_path),
                "file_size": f"{file_size / 1024:.2f} KB",
                "format": file_extension.lstrip(".").upper(),
                "media_type": self._get_media_type(file_extension),
            }
            return ToolResult(output=json.dumps(info, indent=2), system="Image information retrieved successfully")
        except Exception as error:
            return ToolResult(error=f"Error getting image info: {error}")
