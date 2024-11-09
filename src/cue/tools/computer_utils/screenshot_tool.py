import os
import subprocess


def take_screenshot_with_cursor(path):
    """
    Take a screenshot including the mouse cursor using macOS screencapture command

    Args:
        path: Path where to save the screenshot
    """
    # Use macOS screencapture command with -C flag to include cursor
    # -C includes cursor, -x disables the sound
    subprocess.run(["screencapture", "-C", "-x", str(path)])

    if os.path.exists(path):
        return True
    return False
