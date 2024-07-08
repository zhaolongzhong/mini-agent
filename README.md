# mini-agent

This project is designed to explore the expansive capabilities of Large Language Models (LLM) in a compact and accessible format. The goal is to provide a powerful yet minimalistic tool and architecture to help to understand, explore and utilize AI agent effectively. This initiative places a strong emphasis on prompt engineering and is designed to evolve alongside advancements in LLM. **This ensures that the capabilities of the agent will continue to improve and adapt over time.**

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

## Prompt Examples

### Demo 1: read multiple files

Note: multiple tool calls

```
Can you check README.md and run.sh and summarize them?
```

```bash
[2024-06-03 14:02:01 - DEBUG] [chat_completion] process tool calls count: 2
[2024-06-03 14:02:01 - DEBUG] [chat_completion] process tool call <read_file>, args: {'file_path': 'README.md'}
[2024-06-03 14:02:01 - DEBUG] [chat_completion] process tool call <read_file>, args: {'file_path': 'run.sh'}
```

Step 1: respond with 2 tool calls: <read_file>

Step 2: extend the converation with tool responses

Step 3: send completion request to summarize

### Demo 2: multiple steps

Note: multiple tool calls and multiple steps

```
Can you write a fibonacci function to fibo.py and write a test for it? Make sure the test pass?
```

```bash
[User ]: Can you write a fibonacci function to fibo.py and write a test for it? Make sure the test pass?
[2024-06-03 14:06:33 - DEBUG] [chat_completion] process tool calls count: 2
[2024-06-03 14:06:33 - DEBUG] [chat_completion] process tool call <write_to_file>, args: {'file_path': 'fibo.py', 'text': 'def fibonacci(n): ... return b'}
[2024-06-03 14:06:33 - DEBUG] [chat_completion] process tool call <write_to_file>, args: {'file_path': 'test_fibo.py', 'text': 'import unittest\n ... unittest.main()'}
[2024-06-03 14:06:35 - DEBUG] [chat_completion] process tool calls count: 1
[2024-06-03 14:06:35 - DEBUG] [chat_completion] process tool call <execute_shell_command>, args: {'command': 'python -m unittest test_fibo.py'}
```

Step 1: generate fibonacci code and with two tool calls: <write_to_file>

Step 2: write code to fibo.py

Step 3: write test to test_fibo.py

Step 4: run test

## Open Source Function Calling (Tool Use)
 - [groq](https://console.groq.com/docs/tool-use#models): 
    - llama3-70b-8192 (recommend)
    - llama3-8b-8192
    - mixtral-8x7b
    - gemma-7b-it
 - [Together](https://docs.together.ai/docs/function-calling#supported-models): 
    - mistralai/Mixtral-8x7B-Instruct-v0.1