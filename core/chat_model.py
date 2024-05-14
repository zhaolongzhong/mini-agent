from enum import Enum


class ChatModel(Enum):
    """
    Reference: https://platform.openai.com/docs/models/overview
    """

    GPT_4O = "gpt-4o"
    GPT_4O_24_05_13 = "gpt-4o-2024-05-13"
    GPT_4_TURBO_24_04_09 = "gpt-4-turbo-2024-04-09"
