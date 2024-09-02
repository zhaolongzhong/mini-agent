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

## Docker Support

### Building the Docker Image

To build the Docker image for mini-agent, run the following command in the project root directory:

```bash
docker build -t mini-agent .
```

### Running the mini-agent in a Docker Container

After building the image, you can run the mini-agent in a Docker container using:

```bash
docker run -it --env-file .env mini-agent
```

Note: Make sure your `.env` file is properly configured with the necessary API keys before running the container.

### Development with Docker

For development purposes, you can mount your local directory to the container:

```bash
docker run -it --env-file .env -v $(pwd):/app mini-agent
```

This allows you to make changes to the code on your host machine and have them reflected in the container.