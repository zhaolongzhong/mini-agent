# mini-agent

This project is designed to explore the expansive capabilities of Large Language Models (LLM) in a compact and accessible format. The goal is to provide a powerful yet minimalistic tool and architecture to help to understand, explore and utilize AI agent effectively. This initiative places a strong emphasis on prompt engineering and is designed to evolve alongside advancements in LLM. **This ensures that the capabilities of the agent will continue to improve and adapt over time.**

## Agent Capacities
- [Operating System (OS)](./docs/os.md)
- [Coding](./docs/coding.md)

## Set up
Run `./scripts/setup.sh`

## Create .env file

```
cp .env.example .env
```

Update the API keys in the `.env` file

## Run

```bash
./run.sh
```

## Model Configuration
Go to `src/agent_manager.py` to specify a different model.

## Support Models
Check a full list of supported models at `src/llm_client/llm_model.py`.

- [GPT-4o](https://platform.openai.com/docs/models)
- [Claude 3.5](https://docs.anthropic.com/en/docs/about-claude/models)
- [Gemini 1.5 Pro](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/call-gemini-using-openai-library#supported_models)
- All open source Models provided by [Together AI](https://docs.together.ai/docs/chat-models) and [Groq](https://console.groq.com/docs/models)
  - [Gemma 2](https://ai.google.dev/gemma/docs/get_started)
  - [LLama 3](https://llama.meta.com/llama3)
  - [Mixtral](https://github.com/mistralai/mistral-inference)
  - [Qwen 2](https://github.com/QwenLM/Qwen2)

## Open Source Function Calling (Tool Use)
 - [groq](https://console.groq.com/docs/tool-use#models): 
    - llama3-70b-8192 (recommend)
    - llama3-8b-8192
    - mixtral-8x7b
    - gemma-7b-it
 - [Together](https://docs.together.ai/docs/function-calling#supported-models): 
    - mistralai/Mixtral-8x7B-Instruct-v0.1  
