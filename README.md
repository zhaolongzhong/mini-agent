# mini-agent

## Set up

```bash
$ python3 -m venv venv
$ . venv/bin/activate
$ pip install -r requirements.txt
```

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

Promot: read file

```
Can you check run.sh?
```

Prompt: write file

```
Can you write a short story about AGI into story.txt?
```

Prompt: execute python

```
Can you write hello_world.py and print out 'welcome to the future' and run it?
```

```
Can you run tests/test_hello_world.py?
```

Prompt: read, write, execute python script

```
Can you write a fibonacci function to fibo.py and write a test for it? Make sure the test pass?
```

Prompt: gain context

```
Can you check what is this project (./) about?
```
