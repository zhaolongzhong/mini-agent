from rich.text import Text
from rich.theme import Theme
from rich.console import Console

custom_theme = Theme(
    {
        "user": "bold blue",
        "cue": "bold green",
        "error": "bold red",
    }
)

default_console = Console(theme=custom_theme)


class ConsoleUtils:
    def __init__(self):
        self.console = Console(theme=custom_theme)

    def print_msg(self, agent_id: str, message: str) -> None:
        text = Text()
        text.append(f"[{agent_id}]: ", style="cue")
        text.append(str(message), style="cue")
        self.console.print(text)

    def print_error_msg(self, agent_id: str, message: str) -> None:
        text = Text()
        text.append(f"[{agent_id}]: ", style="cue")
        text.append(str(message), style="error")
        self.console.print(text)
