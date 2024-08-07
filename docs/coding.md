# Coding

## Example 1: read multiple files

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

## Example 2: multiple steps

Note: multiple tool calls, run python a script and multiple steps

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
