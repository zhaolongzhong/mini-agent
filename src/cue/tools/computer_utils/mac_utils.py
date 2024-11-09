import os
import logging
import platform
import threading
import subprocess
from typing import Optional

from ..base import ToolResult


class MacUtil:
    def __init__(self):
        self._window_lock = threading.Lock()
        self._last_activation_time = 0
        self._activation_cooldown = 0.5  # seconds
        self.is_main_active = False  # main monitor

    async def normalize_key(self, key: str) -> str:
        """Normalize key names across platforms."""
        key = key.lower().replace("_", "")
        key_map = {
            # Platform-specific mappings
            "super": "command" if platform.system() == "Darwin" else "super",
            "win": "command" if platform.system() == "Darwin" else "win",
            # Common key translations
            "pagedown": "page down",
            "pageup": "page up",
            "pgdn": "page down",
            "pgup": "page up",
            # Enter/Return handling
            "enter": "return",
            # Special keys
            "shift": "shift",
            "space": "space",
            "tab": "tab",
            "escape": "esc",
            # Mac-specific mappings
            "option": "alt" if platform.system() != "Darwin" else "option",
            "alt": "option" if platform.system() == "Darwin" else "alt",
            "ctrl": "control" if platform.system() == "Darwin" else "ctrl",
            "control": "control" if platform.system() == "Darwin" else "control",
            "command": "command",
            "cmd": "command",
        }
        return key_map.get(key, key)

    async def execute_macos_keys(self, keys: list[str]) -> ToolResult:
        """Execute keyboard input on macOS using AppleScript."""
        # Special key codes for MacOS
        key_codes = {
            "down": 125,
            "up": 126,
            "left": 123,
            "right": 124,
            "page down": 121,
            "page up": 116,
            "home": 115,
            "end": 119,
            "return": 36,
            "tab": 48,
            "esc": 53,
            "space": 49,
            "delete": 51,
        }

        if len(keys) == 1:
            key = keys[0]
            if key in key_codes:
                script = f"""
                    tell application "System Events"
                        key code {key_codes[key]}
                    end tell
                """
            else:
                # For regular single keys, use pyautogui
                import pyautogui

                pyautogui.press(key)
                return ToolResult(output="Key pressed successfully")
        else:
            # Handle combination keys
            keystroke = keys[-1]
            modifiers = keys[:-1]
            modifier_str = " down, ".join(modifiers) + " down"

            if keystroke in key_codes:
                script = f"""
                    tell application "System Events"
                        key code {key_codes[keystroke]} using {{{modifier_str}}}
                    end tell
                """
            else:
                script = f"""
                    tell application "System Events"
                        keystroke "{keystroke}" using {{{modifier_str}}}
                    end tell
                """

        result = os.system(f"osascript -e '{script}'")
        return ToolResult(
            output=str(result) if result == 0 else None,
            error=f"AppleScript failed with code {result}" if result != 0 else None,
        )

    def get_main_monitor_bounds(self) -> tuple[int, int, int, int]:
        """Get the bounds of the main monitor (primary display)."""
        if platform.system() != "Darwin":
            return (0, 0, 0, 0)

        script = """
            tell application "System Events"
                set mainBounds to {0, 0, 0, 0}
                set allScreens to {}

                -- Get bounds of all screens
                repeat with i from 1 to (count every desktop)
                    copy bounds of desktop i to end of allScreens
                end repeat

                -- Primary screen is typically the one with the menu bar (y=0)
                repeat with screenBounds in allScreens
                    if item 2 of screenBounds = 0 then
                        set mainBounds to screenBounds
                        exit repeat
                    end if
                end repeat

                return mainBounds
            end tell
        """

        try:
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            output = result.stdout.strip()

            if not output:
                logging.warning("Failed to get monitor bounds from AppleScript")
                # Return bounds for a typical laptop display as fallback
                return (0, 0, 1440, 900)

            try:
                bounds = [int(x.strip()) for x in output.split(",")]
                logging.info(f"Primary monitor bounds: {bounds}")
                return tuple(bounds)
            except ValueError as e:
                logging.error(f"Failed to parse monitor bounds: {e}")
                return (0, 0, 1440, 900)

        except Exception as e:
            logging.error(f"Error getting main monitor bounds: {e}")
            return (0, 0, 1440, 900)

    def is_point_in_main_monitor(self, x: int, y: int) -> bool:
        """Check if the given coordinates are within the main (primary) monitor."""
        x1, y1, x2, y2 = self.get_main_monitor_bounds()

        # If we got invalid bounds, use a conservative check
        if x1 == 0 and y1 == 0 and x2 == 0 and y2 == 0:
            return True  # Assume main monitor to be safe

        # For primary monitor, we don't need to adjust Y coordinate
        # since we're checking against the primary display bounds
        in_bounds = x >= x1 and x <= x2 and y >= 0 and y <= (y2 - y1)

        logging.debug(f"Point ({x}, {y}) in primary monitor: {in_bounds}")
        return in_bounds

    def ensure_active_window(self, x: Optional[int], y: Optional[int]) -> None:
        """
        Ensure window is active with primary monitor detection.
        """
        if x is None or y is None:
            return

        # Update main monitor status
        # is_point_in_main_monitor = self.is_point_in_main_monitor(x, y)
        # self.is_main_active = self.is_point_in_main_monitor(x, y)
        logging.info(f"Primary monitor active: {self.is_main_active}")

        if not self.is_main_active:
            try:
                import pyautogui

                # Move to position safely
                if x == 0 and y == 0:
                    w, h = pyautogui.size()
                    x, y = w // 2, h // 2
                pyautogui.moveTo(x, y, duration=0.3)
                pyautogui.sleep(0.2)

                # Click safely
                pyautogui.click(x, y)
                pyautogui.sleep(0.2)

                logging.info(f"Activated window at ({x}, {y})")
                self.is_main_active = True
            except Exception as e:
                logging.error(f"Failed to activate window: {e}")
