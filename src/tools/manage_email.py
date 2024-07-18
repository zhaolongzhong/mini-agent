import logging

from utils.email_utils import get_email_details, read_email, send_email

logger: logging.Logger = logging.getLogger(__name__)

commands = {
    "read_email_inbox": "read_email_inbox",
    "read_email_detail": "read_email_detail",
    "send": "send",
}


def manage_email(command: str, args: list[str]) -> str | list[any]:
    logger.debug(f"manage_email: {command}, {args}")
    if command == commands["read_email_inbox"]:
        if len(args) > 0:
            max_count = int(args[0])
        else:
            max_count = 10
        return read_email(max_count)
    elif command == commands["read_email_detail"]:
        if len(args) == 0:
            return "Email ID required for reading details."
        email_id = args[0]
        return get_email_details(email_id)
    elif command == commands["send"]:
        if len(args) < 3:
            return "recipient, subject, and message text are required for sending an email."
        recipient, subject, message_text = args[0], args[1], args[2]
        send_email(recipient, subject, message_text)
        return f"Email sent to {recipient}"
    else:
        return "Command not found."
