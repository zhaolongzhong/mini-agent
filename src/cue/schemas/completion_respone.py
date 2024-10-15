from typing import Any, Optional, Union


class CompletionResponse:
    def __init__(self, model: str, response: Optional[Any] = None, error: Optional[Any] = None):
        self.model = model
        self.response = response
        self.error = error

    def get_text(self) -> Union[str, list[dict]]:
        if self.response is None:
            return str(self.error)

        if "claude" in self.model:
            return self.response.content[0].text
        return self.response.choices[0].message.content

    def __str__(self):
        return f"Text: {self.get_text()}"
