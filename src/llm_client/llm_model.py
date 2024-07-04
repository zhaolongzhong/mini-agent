from enum import Enum


class ChatModel(Enum):
    # Claude https://docs.anthropic.com/en/docs/about-claude/models#model-names
    CLAUDE_3_OPUS_20240229 = "claude-3-opus-20240229"
    CLAUDE_3_5_SONNET_20240620 = "claude-3-5-sonnet-20240620"

    # Gemini https://ai.google.dev/gemini-api/docs/models/gemini#model-variations
    GEMINI_1_5_FLASH = "gemini-1.5-flash"
    GEMINI_1_5_PRO = "gemini-1.5-pro"

    # OpenAI https://platform.openai.com/docs/models/overview
    GPT_4O = "gpt-4o"
    GPT_4O_24_05_13 = "gpt-4o-2024-05-13"
    GPT_4_TURBO_24_04_09 = "gpt-4-turbo-2024-04-09"

    def short_name(self) -> str:
        if "claude" in self:
            return "claude"
        elif "gemini" in self:
            return "gemini"
        elif "gpt-4" in self:
            return "gpt"
        else:
            return "unknown"
