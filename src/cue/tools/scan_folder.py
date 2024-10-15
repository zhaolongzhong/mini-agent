import os


def scan_folder(folder_path, depth=2):
    """
    Scan a directory up to a certain depth, ignoring folders that start with a dot.
    The default depth is 2.
    """
    ignore_patterns = [".*", "__pycache__"]
    file_paths = []

    for subdir, dirs, files in os.walk(folder_path):
        dirs[:] = [d for d in dirs if not any(d.startswith(pattern) or d == pattern for pattern in ignore_patterns)]

        if subdir.count(os.sep) - folder_path.count(os.sep) >= depth:
            del dirs[:]
            continue

        for file in files:
            file_paths.append(os.path.join(subdir, file))

    return file_paths
