import os
import subprocess


def read_file(file_path: str, encoding: str = "utf-8") -> str:
    """Read a file and return its contents as a string."""
    if not os.path.isfile(file_path):
        return f"Error: The file {file_path} does not exist."

    try:
        with open(file_path, encoding=encoding) as f:
            return f.read()
    except Exception as error:
        return f"Error: {error}"


def write_to_file(file_path: str, text: str, encoding: str = "utf-8") -> str:
    """Write string content to a file."""
    try:
        # Creating the directory if it does not exist
        directory = os.path.dirname(file_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        # Writing text to the file
        with open(file_path, "w", encoding=encoding) as f:
            f.write(text)
        return "File written successfully."
    except Exception as error:
        return f"Error: {error}"


def run_python_script(script_name):
    try:
        result = subprocess.run(
            ["python", script_name], capture_output=True, text=True, check=True
        )
        print(f"Run script output:\n{result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"Run script error: {e}")
