import os

from pypdf import PdfReader


def read_file(file_path: str, encoding: str = "utf-8") -> str:
    """Read a file (text or PDF) and return its contents as a string."""
    if not os.path.isfile(file_path):
        return f"Error: The file {file_path} does not exist."

    try:
        if file_path.lower().endswith(".pdf"):
            reader = PdfReader(file_path)
            text = "".join(page.extract_text() for page in reader.pages)
        else:
            with open(file_path, encoding=encoding) as f:
                text = f.read()
        original_length = len(text)
        max_lenth = 5000
        if original_length > max_lenth:
            visible_text = text[:max_lenth]
            visibility_percentage = (max_lenth / original_length) * 100
            visibility_info = f"\n\n[Truncated to {max_lenth} characters, visibility: {visibility_percentage:.2f}%]"
            return visible_text + visibility_info
        else:
            return text
    except Exception as error:
        return f"Error: {error}"
