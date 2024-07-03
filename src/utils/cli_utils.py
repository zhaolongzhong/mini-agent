import asyncio
import itertools
import sys


def clear_line():
    """Clears the current line in the console."""
    sys.stdout.write("\r")
    sys.stdout.flush()


async def progress_indicator():
    spinner = itertools.cycle(["|", "/", "-", "\\"])
    try:
        while True:
            sys.stdout.write(f"\r{next(spinner)}")  # Print the spinner character
            sys.stdout.flush()
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        clear_line()
