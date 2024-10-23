import logging
from typing import ClassVar, Literal, Union

from .base import BaseTool
from .utils.drive_utils import (
    create_folder,
    download_file,
    get_by_folder_id,
    get_files_or_folders,
    upload_file_to_folder,
)

logger: logging.Logger = logging.getLogger(__name__)

commands = {
    "get_files_or_folders": "get_files_or_folders",
    "get_by_folder_id": "get_by_folder_id",
    "download_file": "download_file",
    "create_folder": "create_folder",
    "upload_file_to_folder": "upload_file_to_folder",
}


class GoogleDriveTool(BaseTool):
    """A tool that allows the agent to manage email."""

    name: ClassVar[Literal["drive"]] = "drive"

    def __init__(self):
        super().__init__()

    async def __call__(self, command: str, args: list[str]) -> Union[str, list[any]]:
        return await self.drive(command, args)

    async def drive(self, command: str, args: list[str]) -> Union[str, list[any]]:
        """Handle Google Drive operations like listing, downloading, and managing files/folders.

        Args:
            command (str): Operation to perform. Options are:
                - 'get_files_or_folders': [query, page_size]
                - 'get_by_folder_id': [folder_id]
                - 'download_file': [file_id, file_name, directory]
                - 'create_folder': [folder_name, parent_folder_id?]
                - 'upload_file_to_folder': [file_name, folder_id]
            args (list[str]): Command arguments as described above.

        Returns:
            Union[str, list[any]]: Operation result or error message.

        """
        logger.debug(f"drive: {command}, {args}")
        if command == commands["get_files_or_folders"]:
            if len(args) > 0:
                query = args[0]
                if len(args) > 1:
                    page_size = int(args[1])
                else:
                    page_size = 10
                return get_files_or_folders(query, page_size)
            else:
                return get_files_or_folders()
        elif command == commands["get_by_folder_id"]:
            if len(args) == 0:
                return "Folder ID required for getting files."
            folder_id = args[0]
            return get_by_folder_id(folder_id)
        elif command == commands["download_file"]:
            if len(args) < 2:
                return "File ID and file name are required for downloading a file."
            file_id, file_name = args[0], args[1]
            directory = args[2] if len(args) > 2 else "."
            return download_file(file_id, file_name, directory)
        elif command == commands["create_folder"]:
            if len(args) == 0:
                return "Folder name is required for creating a folder and parent_folder_id is optional."
            folder_name = args[0]
            parent_folder_id = args[1] if len(args) > 1 else None
            return create_folder(folder_name, parent_folder_id)
        elif command == commands["upload_file_to_folder"]:
            if len(args) < 2:
                return "File name and folder ID are required for uploading a file."
            file_name, folder_id = args[0], args[1]
            return upload_file_to_folder(file_name, folder_id)
        else:
            return "Invalid command. Please ensure the function signature is 'handle_drive_command(command, args)' with a valid command and corresponding arguments."
