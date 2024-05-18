from llm_client.clients import create_openai_client


class LLMClient:
    def __init__(self, api_key: str):
        self.client = create_openai_client(api_key)

    async def send_request(
        self,
        model: str,
        messages: list,
        tools: list = [],
        tool_choice: str = "auto",
    ):
        return await self.client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
        )
