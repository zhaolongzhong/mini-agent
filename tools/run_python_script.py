import subprocess


def run_python_script(script_name):
    try:
        result = subprocess.run(
            ["python", script_name], capture_output=True, text=True, check=True
        )
        print(f"Run script output:\n{result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"Run script error: {e}")
