import json
import logging
from typing import ClassVar, Literal

from .base import BaseTool, ToolResult
from .utils.email_utils import get_email_details, read_email, send_email

logger: logging.Logger = logging.getLogger(__name__)

commands = {
    "read_inbox": "read_inbox",
    "read_detail": "read_detail",
    "send": "send",
}


class EmailTool(BaseTool):
    """A tool that allows the agent to manage email."""

    name: ClassVar[Literal["email"]] = "email"

    def __init__(self):
        super().__init__()

    async def __call__(self, command: str, args: list[str]) -> ToolResult:
        return await self.email(command, args)

    async def email(self, command: str, args: list[str]) -> ToolResult:
        """Manage emails, including reading inbox, reading email details, and sending emails.

        Args:
            command (str): Operation to perform. Options are:
                - 'read_inbox': Get list of emails [max_count=10]
                - 'read_detail': Get email content [email_id]
                - 'send': Send new email [recipient, subject, content]
            args (list[str]): Command arguments.

        Returns:
            ToolResult: Email operation result or error message.

        """
        logger.debug(f"email: {command}, {args}")
        if command == commands["read_inbox"]:
            if len(args) > 0:
                max_count = int(args[0])
            else:
                max_count = 10
            emails_dict = read_email(max_count)  # return a list of email dict
            return ToolResult(output=", ".join(emails_dict))
        elif command == commands["read_detail"]:
            if len(args) == 0:
                return "Email ID required for reading details."
            email_id = args[0]
            email_detail = get_email_details(email_id)
            return ToolResult(output=json.dumps(email_detail))
        elif command == commands["send"]:
            if len(args) < 3:
                return "recipient, subject, and message text are required for sending an email."
            recipient, subject, message_text = args[0], args[1], args[2]
            res = send_email(recipient, subject, message_text)
            return ToolResult(output=res)
        else:
            return ToolResult(error="Command not found.")
