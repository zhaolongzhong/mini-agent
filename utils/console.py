import sys


def clear_line():
    """Clears the current line in the console."""
    sys.stdout.write("\r")
    sys.stdout.flush()
