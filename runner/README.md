# Cue Runner

## Overview

The Cue Runner is a process manager that enables self-managed operation of the Cue agent system. It provides:

- Automatic process recovery
- Self-management capabilities
- Process status monitoring
- Agent-initiated restart capability

## Cue Runner Setup Guide

### Directory Structure

```
cue/
├── pyproject.toml
└── runner/
    ├── README.md
    ├── cue_runner/
    │   ├── __init__.py
    │   ├── cli.py
    │   ├── commands/
    │   ├── config.py
    │   ├── formatting.py
    │   └── process_manager.py
    ├── pyproject.toml
    ├── run_cue.py
    ├── setup.sh
```

### Setup Steps

1. Install dependencies:

```
cd cue
./runner/setup.sh
```

### Start a runner

```
 cue-r start -r runner_a
```

### Check Runner Status

```
cue-r status -r runner_a
```

## Examples

```bash
(.venv) ~/cue/runner$ cue-r

 Usage: cue-r [OPTIONS] COMMAND [ARGS]...

 Manage Cue runner processes

╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --version             -V        Show version and exit                                                                                                                                           │
│ --help                -h        Show this help message                                                                                                                                          │
│ --verbose             -v        Show verbose output                                                                                                                                             │
│ --install-completion            Install completion for the current shell.                                                                                                                       │
│ --show-completion               Show completion for the current shell, to copy it or customize the installation.                                                                                │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ list     List runners and their status                                                                                                                                                          │
│ status   Show runner status                                                                                                                                                                     │
│ kill     Kill runner processes                                                                                                                                                                  │
│ clean    Clean or verify runner files                                                                                                                                                           │
│ start    Start runner processes                                                                                                                                                                 │
│ stop     Stop runner processes                                                                                                                                                                  │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

(.venv) ~/cue/runner$ cue-r list
Found 1 runners:
==================================================
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Property     ┃ Value                      ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Runner ID    │ default                    │
│ Status       │ ACTIVE                     │
│ Directory    │ /tmp/cue_runners/default   │
│ PID          │ 14790                      │
│ Last Check   │ 2024-11-15T19:38:57.806139 │
│ CPU Usage    │ 0.0%                       │
│ Memory Usage │ 15.5 MB                    │
└──────────────┴────────────────────────────┘
(.venv) ~/cue/runner$ cue-r start -r runner_a
Runner started successfully
┏━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Property  ┃ Value                                 ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Runner ID │ runner_a                              │
│ Status    │ Started                               │
│ PID       │ 16668                                 │
│ Log File  │ /tmp/cue_runners/runner_a/runner.log  │
└───────────┴───────────────────────────────────────┘
(.venv) ~/cue/runner$ cue-r list
Found 2 runners:
==================================================
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Property     ┃ Value                      ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Runner ID    │ runner_a                   │
│ Status       │ ACTIVE                     │
│ Directory    │ /tmp/cue_runners/runner_a  │
│ PID          │ 16668                      │
│ Last Check   │ 2024-11-15T19:39:08.956118 │
│ CPU Usage    │ 0.0%                       │
│ Memory Usage │ 18.5 MB                    │
└──────────────┴────────────────────────────┘
==================================================
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Property     ┃ Value                      ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Runner ID    │ default                    │
│ Status       │ ACTIVE                     │
│ Directory    │ /tmp/cue_runners/default   │
│ PID          │ 14790                      │
│ Last Check   │ 2024-11-15T19:39:12.893620 │
│ CPU Usage    │ 0.0%                       │
│ Memory Usage │ 15.5 MB                    │
└──────────────┴────────────────────────────┘
(.venv) ~/cue/runner$ cue-r stop -r runner_a
Stop runner 'runner_a'? [y/N]: y
┏━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━┓
┃ Runner ID ┃ PID   ┃ Status  ┃
┡━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━┩
│ runner_a  │ 16668 │ Success │
└───────────┴───────┴─────────┘
(.venv) ~/cue/runner$ cue-r list
Found 1 runners:
==================================================
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Property     ┃ Value                      ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Runner ID    │ default                    │
│ Status       │ ACTIVE                     │
│ Directory    │ /tmp/cue_runners/default   │
│ PID          │ 14790                      │
│ Last Check   │ 2024-11-15T19:40:35.336452 │
│ CPU Usage    │ 0.0%                       │
│ Memory Usage │ 15.5 MB                    │
└──────────────┴────────────────────────────┘
(.venv) ~/cue/runner$
```
