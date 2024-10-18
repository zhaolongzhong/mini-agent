# Tool use evals

Build and copy agent client to assets folder

```
rye build
cp  dist/*.whl evals/tool_use/assets
```

Run in container

```

cd evals/tool_use
python run_evals.py
```

Run in locally

```
source .venv/bin/activate
cd evals/tool_use
python run_evals_locally.py
```
