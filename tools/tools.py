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


def scan_folder(folder_path, depth=2):
    """
    Scan a directory up to a certain depth, ignoring folders that start with a dot.
    The default depth is 2.
    """
    ignore_patterns = [".*", "__pycache__"]
    file_paths = []

    for subdir, dirs, files in os.walk(folder_path):
        dirs[:] = [
            d
            for d in dirs
            if not any(
                d.startswith(pattern) or d == pattern for pattern in ignore_patterns
            )
        ]

        if subdir.count(os.sep) - folder_path.count(os.sep) >= depth:
            del dirs[:]
            continue

        for file in files:
            file_paths.append(os.path.join(subdir, file))

    return file_paths


def run_python_script(script_name):
    try:
        result = subprocess.run(
            ["python", script_name], capture_output=True, text=True, check=True
        )
        print(f"Run script output:\n{result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"Run script error: {e}")
