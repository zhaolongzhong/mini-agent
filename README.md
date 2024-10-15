# Cue

A lightweight multi-agent system.

Cue is designed to explore the potential of multi-agent systems powered by Large Language Models (LLMs) in a minimal and efficient format. This project aims to showcase how a small-scale, yet powerful, architecture can leverage LLMs to orchestrate intelligent agents.

## Getting Started

### Step 1: Clone repository

```
git clone git@github.com:zhaolongzhong/mini-agent.git
```

### Step 2: Setup the Environment

Run the setup script to install dependencies and ensure your environment is ready:

```
./scripts/setup.sh
```

This script will:

- Check if Rye is installed and install it if necessary.
- Configure Rye and sync project dependencies.

### Step 3: Create the `.env` File

```
cp .env.example src/cue/.env
```

Update the API keys in the `.env` file with your own credentials.

### Step 4: Run command line

Start the command line:

```
rye run cue -r
```

or activiate virtual environment and run `cue` command directly.

```
source .venv/bin/activate
```

```
$ cue -v
version 0.1.0
```

```
$ cue -h
usage: cue [-h] [-v] [-r] [-c] [--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}] [--log-file LOG_FILE]

Cue CLI: An interactive asynchronous client.

optional arguments:
  -h, --help            show this help message and exit
  -v, --version         Print the version of the Cue client.
  -r, --run             Run the interactive CLI.
  -c, --config          Print the default configuration.
  --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Set the logging level (overrides environment variable).
  --log-file LOG_FILE   Path to a file to log messages (overrides environment settings).
```

You can also run using the following script:

```
./scripts/run.sh
```

## Additional Information

- **Dependencies**: Dependencies are managed using Rye, which simplifies package management and setup.
- **Scripts**: The `setup.sh` script handles the installation of dependencies, while `run.sh` starts the CLI client in development mode.
- **Environment**: Ensure you update the `.env` file with the necessary API keys before running the application.

For more detailed documentation or troubleshooting, please refer to the project documentation.

## Testing

Run tests located in the `tests` directory using `./scripts/test.sh`.

**Note**: Running basic evaluation test requires `OPENAI_API_KEY` in `src/cue/.env`

```
$ ./scripts/test.sh -h
Usage: ./scripts/test.sh [options]

Options:
  -u    Run unit tests only
  -i    Run integration tests only
  -a    Run both unit and integration tests
  -e    Run basic evaluation tests (requires OPENAI_API_KEY)
  -h    Show this help message and exit

Examples:
  ./scripts/test.sh -u          # Run unit tests only
  ./scripts/test.sh -i          # Run integration tests only
  ./scripts/test.sh -a          # Run both unit and integration tests
  ./scripts/test.sh -e          # Run evaluation tests
  ./scripts/test.sh -u -e       # Run unit and evaluation tests
```

## Evaluation

Run full evaluations from the `evals` directory using `./scripts/run_evals.sh`. For more details, refer to `evals/README.md`.

## Agent Capacities

- [Operating System (OS)](./docs/os.md)
- [Coding](./docs/coding.md)

## Model Configuration

Go to `src/agent_manager.py` to specify a different model.

## Support Models

Check a full list of supported models at `src/cue/llm/llm_model.py`.

- [GPT-4o](https://platform.openai.com/docs/models)
- [Claude 3.5](https://docs.anthropic.com/en/docs/about-claude/models)
- [Gemini 1.5 Pro](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/call-gemini-using-openai-library#supported_models)

## Project Structure

```
- credentials/       # Contains authentication files and keys
- docs/              # Documentation for the project
- evals/             # Evaluation scripts and results
- logs/              # Log files for debugging and analysis
- src/cue/           # Main source code
  - cli/             # Interactive async client
  - _client          # Asynchronous client module
- tests/             # Test cases for various modules
```
