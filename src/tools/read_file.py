import os


def read_file(file_path: str, encoding: str = "utf-8") -> str:
    """Read a file and return its contents as a string."""
    if not os.path.isfile(file_path):
        return f"Error: The file {file_path} does not exist."

    try:
        with open(file_path, encoding=encoding) as f:
            return f.read()
    except Exception as error:
        return f"Error: {error}"
