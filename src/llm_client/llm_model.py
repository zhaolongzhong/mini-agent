import os
from enum import Enum


class ChatModel(Enum):
    # Claude https://docs.anthropic.com/en/docs/about-claude/models#model-names
    CLAUDE_3_OPUS_20240229 = ("claude-3-opus-20240229", True, "anthropic")
    CLAUDE_3_5_SONNET_20240620 = ("claude-3-5-sonnet-20240620", True, "anthropic")

    # Gemini https://ai.google.dev/gemini-api/docs/models/gemini#model-variations
    # https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/call-gemini-using-openai-library#supported_models
    GEMINI_1_5_FLASH = ("gemini-1.5-flash", True, "google")
    GEMINI_1_5_PRO = ("gemini-1.5-pro", True, "google")

    # OpenAI https://platform.openai.com/docs/models/overview
    GPT_4O = ("gpt-4o", True, "openai")
    GPT_4O_MINI = ("gpt-4o-mini", True, "openai")
    GPT_4O_24_05_13 = ("gpt-4o-2024-05-13", True, "openai")
    GPT_4_TURBO_24_04_09 = ("gpt-4-turbo-2024-04-09", True, "openai")

    # LLAMA
    ## https://console.groq.com/docs/tool-use#models
    LLAMA3_70B_8192_GROQ = ("llama3-70b-8192", True, "groq")  # only model we currently recommend using for tool use
    LLAMA3_8B_8192_GROQ = ("llama3-8b-8192", True, "groq")
    LLAMA_3_70B_CHAT_HF_TOGETHER = ("meta-llama/Llama-3-70b-chat-hf", False, "together")
    LLAMA_3_70B_TOGETHER = ("meta-llama/Meta-Llama-3-70B", False, "together")

    # MIXTRAL
    MIXTRAL_8X7B_32768_TOGETHER = ("mixtral-8x7b-32768", True, "together")
    MISTRALAI_MISTRAL_8X7B_INSTRUCT_V0_1_TOGETHER = ("mistralai/mixtral-8x7b-instruct-v0.1", True, "together")

    # GEMMA
    GEMMA2_9B_IT_GROQ = ("gemma2-9b-it", False, "groq")

    # Qwen
    QWEN_2_72B_INSTRUCT_TOGETHER = ("qwen/qwen2-72b-instruct", False, "together")

    def __init__(self, id, allows_tool_use, key_prefix):
        self.id = id
        self.allows_tool_use = allows_tool_use
        self.key_prefix = key_prefix

    @property
    def model_id(self) -> str:
        return self.id

    @property
    def tool_use_allowed(self):
        return self.allows_tool_use

    @property
    def api_key_env(self) -> str:
        return f"{self.key_prefix.upper()}_API_KEY"


def get_api_key(model: ChatModel) -> str:
    api_key = os.getenv(model.api_key_env)
    if not api_key:
        raise ValueError(f"API key for {model.api_key_env} not found in environment variables")
    return api_key
