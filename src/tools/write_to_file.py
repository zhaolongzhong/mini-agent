import os


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
