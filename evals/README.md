# Agent Evaluation (Experimental)

## Overview

We are currently experimenting with [METR](https://metr.org/), a widely used evaluation framework adopted by companies such as Anthropic and OpenAI. METR has been at the forefront of collaborative efforts in model evaluation, including recent advancements in frontier model assessments[^o1-meter-eval][^gpt-4-claude].

- [METER Task Standard](https://github.com/METR/task-standard)

To facilitate seamless integration with this evaluation framework and to evaluate agents across different dimensions, we’ve developed a Python client (`CueAsyncClient`) that provides maximum flexibility for agent configurations.

Additionally, evaluations are run within Docker containers to ensure:

- **Safety**: Isolated environments reduce risk.
- **Standardization**: Contributors can run the evaluations consistently within the same development environment.
- **Scalability**: Easily run evaluations in parallel to handle larger workloads efficiently.

[^o1-meter-eval]: [Details on METR’s preliminary evaluation of OpenAI o1-preview](https://metr.github.io/autonomy-evals-guide/openai-o1-preview-report/)
[^gpt-4-claude]: [Update on general capability evaluations](https://metr.org/blog/2024-08-06-update-on-evaluations/)

## Getting Started

```sh
./scripts/run_evals.sh
```
