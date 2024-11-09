# Reference: https://github.com/anthropics/anthropic-quickstarts/blob/main/computer-use-demo/computer_use_demo/tools/computer.py
import os
import time
import shlex
import base64
import shutil
import asyncio
import logging
import platform
from enum import Enum
from uuid import uuid4
from typing import Literal, Optional, TypedDict
from pathlib import Path

from .run import run
from .base import BaseTool, ToolError, ToolResult
from .computer_utils.mac_utils import MacUtil
from .computer_utils.screenshot_tool import take_screenshot_with_cursor
from .computer_utils.ui_component_detector import get_bounding_box_info

if platform.system() == "Darwin":
    import pyautogui

    pyautogui.FAILSAFE = True
else:
    pyautogui = None

logger = logging.getLogger(__name__)

OUTPUT_DIR = "/tmp/outputs"

TYPING_DELAY_MS = 12
TYPING_GROUP_SIZE = 50

Action = Literal[
    "key",
    "type",
    "mouse_move",
    "left_click",
    "left_click_drag",
    "right_click",
    "middle_click",
    "double_click",
    "screenshot",
    "cursor_position",
]


class Resolution(TypedDict):
    width: int
    height: int


# sizes above XGA/WXGA are not recommended (see README.md)
# scale down to one of these targets if ComputerTool._scaling_enabled is set
MAX_SCALING_TARGETS: dict[str, Resolution] = {
    "XGA": Resolution(width=1024, height=768),  # 4:3
    "WXGA": Resolution(width=1280, height=800),  # 16:10
    "FWXGA": Resolution(width=1366, height=768),  # ~16:9
}


class StrEnum(str, Enum):
    pass


class ScalingSource(StrEnum):
    COMPUTER = "computer"
    API = "api"


class ComputerToolOptions(TypedDict):
    display_height_px: int
    display_width_px: int
    display_number: Optional[int]


def chunks(s: str, chunk_size: int) -> list[str]:
    return [s[i : i + chunk_size] for i in range(0, len(s), chunk_size)]


class ComputerTool(BaseTool):
    """
    A tool that allows the agent to interact with the screen, keyboard, and mouse of the current computer.
    """

    name: Literal["computer"] = "computer"
    width: int
    height: int
    display_num: Optional[int]

    _screenshot_delay = 2.0
    _scaling_enabled = True
    _mouse_move_duration = 1.0

    @property
    def options(self) -> ComputerToolOptions:
        width, height = self.scale_coordinates(ScalingSource.COMPUTER, self.width, self.height)
        return {
            "display_width_px": width,
            "display_height_px": height,
            "display_number": self.display_num,
        }

    def __init__(self):
        self._function = self.computer
        super().__init__()

        self.width = int(os.getenv("WIDTH") or 0)
        self.height = int(os.getenv("HEIGHT") or 0)

        if platform.system() == "Darwin":
            self.width, self.height = pyautogui.size()
        assert self.width and self.height, "WIDTH, HEIGHT must be set"
        if (display_num := os.getenv("DISPLAY_NUM")) is not None:
            self.display_num = int(display_num)
            self._display_prefix = f"DISPLAY=:{self.display_num} "
        else:
            self.display_num = None
            self._display_prefix = ""

        self.xdotool = f"{self._display_prefix}xdotool"
        self.last_mouse_position: Optional[tuple[int, int]] = (0, 0)
        self.mac_util = MacUtil() if platform.system() == "Darwin" else None

    async def __call__(
        self,
        *,
        action: Action,
        text: Optional[str] = None,
        coordinate: Optional[tuple[int, int]] = None,
        **kwargs,
    ):
        return await self.computer(action=action, text=text, coordinate=coordinate, **kwargs)

    async def computer(
        self,
        *,
        action: Action,
        text: Optional[str] = None,
        coordinate: Optional[tuple[int, int]] = None,
        **kwargs,
    ) -> ToolResult:
        logger.debug(
            f"computer - action: {action}, coordinate: {coordinate}, self.last_mouse_position: {self.last_mouse_position}"
        )
        if action in ("mouse_move", "left_click_drag"):
            if coordinate is None:
                raise ToolError(f"coordinate is required for {action}")
            if text is not None:
                raise ToolError(f"text is not accepted for {action}")
            if not isinstance(coordinate, list) or len(coordinate) != 2:
                raise ToolError(f"{coordinate} must be a tuple of length 2")
            if not all(isinstance(i, int) and i >= 0 for i in coordinate):
                raise ToolError(f"{coordinate} must be a tuple of non-negative ints")

            x, y = self.scale_coordinates(ScalingSource.API, coordinate[0], coordinate[1])
            self.last_mouse_position = (x, y)
            logger.debug(f"after {action}, self.last_mouse_position: {self.last_mouse_position}")

            if action == "mouse_move":
                if platform.system() == "Darwin":
                    return await self.move_mouse_to(x, y)
                return await self.shell(f"{self.xdotool} mousemove --sync {x} {y}")
            elif action == "left_click_drag":
                if platform.system() == "Darwin":
                    return await self.left_click_drag(x, y)
                return await self.shell(f"{self.xdotool} mousedown 1 mousemove --sync {x} {y} mouseup 1")

        if action in ("key", "type"):
            if text is None:
                raise ToolError(f"text is required for {action}")
            if coordinate is not None:
                raise ToolError(f"coordinate is not accepted for {action}")
            if not isinstance(text, str):
                raise ToolError(output=f"{text} must be a string")

            if platform.system() == "Darwin":  # macOS
                if action == "key":
                    # Split and normalize keys
                    keys = [await self.mac_util.normalize_key(k) for k in text.split("+")]
                    try:
                        x, y = self.last_mouse_position
                        self.mac_util.ensure_active_window(x, y)
                    except Exception as e:
                        logger.error(f"Ran into error check if point is in active window or not: {e}")

                    logger.debug(f"execute_macos_keys keys: {keys}")
                    return await self.mac_util.execute_macos_keys(keys)
                elif action == "type":
                    logger.debug(f"action - type: {text}")
                    for chunk in chunks(text, TYPING_GROUP_SIZE):
                        logger.debug(f"action - type: {text}, write chunk: {chunk}")
                        time.sleep(0.1)
                        pyautogui.write(chunk)
                    screenshot_base64 = (await self.screenshot()).base64_image
                    return ToolResult(
                        output="Check screenshot to see if it's correctly typed or not.", base64_image=screenshot_base64
                    )
            else:
                if action == "key":
                    return await self.shell(f"{self.xdotool} key -- {text}")
                elif action == "type":
                    results: list[ToolResult] = []
                    for chunk in chunks(text, TYPING_GROUP_SIZE):
                        cmd = f"{self.xdotool} type --delay {TYPING_DELAY_MS} -- {shlex.quote(chunk)}"
                        results.append(await self.shell(cmd, take_screenshot=False))
                    screenshot_base64 = (await self.screenshot()).base64_image
                    return ToolResult(
                        output="".join(result.output or "" for result in results),
                        error="".join(result.error or "" for result in results),
                        base64_image=screenshot_base64,
                    )

        if action in (
            "left_click",
            "right_click",
            "double_click",
            "middle_click",
            "screenshot",
            "cursor_position",
        ):
            if text is not None:
                raise ToolError(f"text is not accepted for {action}")
            if coordinate is not None:
                # sometimes it still return coordinate even we
                logger.error(f"coordinate is not accepted for {action}")
                raise ToolError(f"coordinate is not accepted for {action}")

            if action == "screenshot":
                return await self.screenshot()
            elif action == "cursor_position":
                x, y = await self.get_cursor_position()
                return ToolResult(output=f"X={x},Y={y}")
            elif action in ["left_click", "right_click", "middle_click", "double_click"]:
                try:
                    if coordinate is None:
                        coordinate = self.last_mouse_position
                        c_x, c_y = await self.get_cursor_position()
                    x, y = coordinate
                    if platform.system() == "Darwin":
                        self.mac_util.ensure_active_window(x, y)
                    else:
                        await self.shell(f"{self.xdotool} mousemove {x} {y}")
                except Exception as e:
                    logger.error(f"Ran into error when {action}, {e}")
                c_x, c_y = await self.get_cursor_position()
                logger.debug(
                    f"{action}, last_mouse_position: {self.last_mouse_position}, latest: c_x, c_y: {c_x}, {c_y}"
                )
                res = await self.click(action)
                return res

            else:
                raise ToolError(f"Unsupported action: {action}")

        raise ToolError(f"Invalid action: {action}")

    async def get_cursor_position(self) -> tuple[int, int]:
        """Get current cursor position using platform-appropriate method."""
        if platform.system() == "Darwin":
            x, y = pyautogui.position()
            scaled_x, scaled_y = self.scale_coordinates(ScalingSource.COMPUTER, x, y)
            return scaled_x, scaled_y
        else:
            result = await self.shell(
                f"{self.xdotool} getmouselocation --shell",
                take_screenshot=False,
            )
            output = result.output or ""
            x = int(output.split("X=")[1].split("\n")[0])
            y = int(output.split("Y=")[1].split("\n")[0])
            return self.scale_coordinates(ScalingSource.COMPUTER, x, y)

    async def screenshot(self):
        """Take a screenshot of the current screen and return the base64 encoded image."""
        output_dir = Path(OUTPUT_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"screenshot_{uuid4().hex}.png"

        if platform.system() != "Darwin":
            # Try gnome-screenshot first
            if shutil.which("gnome-screenshot"):
                screenshot_cmd = f"{self._display_prefix}gnome-screenshot -f {path} -p"
            else:
                # Fall back to scrot if gnome-screenshot isn't available
                screenshot_cmd = f"{self._display_prefix}scrot -p {path}"

            result = await self.shell(screenshot_cmd, take_screenshot=False)
            if self._scaling_enabled:
                x, y = self.scale_coordinates(ScalingSource.COMPUTER, self.width, self.height)
                await self.shell(f"convert {path} -resize {x}x{y}! {path}", take_screenshot=False)

            if path.exists():
                return result.replace(base64_image=base64.b64encode(path.read_bytes()).decode())
        else:
            take_screenshot_with_cursor(str(path))
            if self._scaling_enabled:
                x, y = self.scale_coordinates(ScalingSource.COMPUTER, self.width, self.height)
                logger.debug(
                    f"_scaling_enabled, screen size:({self.width},{self.height}), after scale_coordinates, (x,y): ({x},{y}), "
                )
                from PIL import Image

                with Image.open(path) as img:
                    img = img.resize((x, y), Image.Resampling.LANCZOS)
                    img.save(path)
            if path.exists():
                logger.debug(f"Tool screenshot successfully at {path}")
                base64_image = base64.b64encode(path.read_bytes()).decode()
                components_info = get_bounding_box_info(str(path))
                path.unlink()
                return ToolResult(
                    base64_image=base64_image, output=f"Bounding boxes for UI components: {components_info}"
                )

        logger.error(f"Ran into error when take screenshot: {result.error}")
        raise ToolError(f"Failed to take screenshot: {result.error}")

    async def shell(self, command: str, take_screenshot=True) -> ToolResult:
        """Run a shell command and return the output, error, and optionally a screenshot."""
        logger.debug(f"shell: {command}, take_screenshot: {take_screenshot}")
        try:
            _, stdout, stderr = await run(command)
            base64_image = None
            logger.debug(
                f"shell: {command}, take_screenshot: {take_screenshot}, run result stdout:{stdout}, stderr: {stderr}"
            )
            if take_screenshot:
                # delay to let things settle before taking a screenshot
                await asyncio.sleep(self._screenshot_delay)
                base64_image = (await self.screenshot()).base64_image
            return ToolResult(output=stdout, error=stderr, base64_image=base64_image)
        except Exception as e:
            logger.error(f"Ran into error when run shell command: {e}")
            raise ToolError(f"Failed to run shell command '{command}': {e}")

    def scale_coordinates(self, source: ScalingSource, x: int, y: int):
        """Scale coordinates to a target maximum resolution."""
        if not self._scaling_enabled:
            return x, y
        ratio = self.width / self.height
        target_dimension = None
        for dimension in MAX_SCALING_TARGETS.values():
            # allow some error in the aspect ratio - not ratios are exactly 16:9
            if abs(dimension["width"] / dimension["height"] - ratio) < 0.02:
                if dimension["width"] < self.width:
                    target_dimension = dimension
                break
        if target_dimension is None:
            return x, y
        # should be less than 1
        x_scaling_factor = target_dimension["width"] / self.width
        y_scaling_factor = target_dimension["height"] / self.height
        if source == ScalingSource.API:
            if x > self.width or y > self.height:
                raise ToolError(f"Coordinates {x}, {y} are out of bounds")
            # scale up
            return round(x / x_scaling_factor), round(y / y_scaling_factor)
        # scale down
        return round(x * x_scaling_factor), round(y * y_scaling_factor)

    async def _delay_screenshot(self, take_screenshot: bool = True) -> ToolResult:
        if take_screenshot:
            # delay to let things settle before taking a screenshot
            await asyncio.sleep(self._screenshot_delay)
            return await self.screenshot()
        return None

    async def move_mouse_to(self, x, y, take_screenshot=True) -> ToolResult:
        logger.debug(f"move_mouse_to: {x},{y}")
        pyautogui.moveTo(x, y, self._mouse_move_duration)
        self.mac_util.ensure_active_window(x, y)
        await asyncio.sleep(self._screenshot_delay)
        result = await self._delay_screenshot(take_screenshot)
        return ToolResult(
            output=f"move_mouse result: screen size w:{self.width}, h:{self.height}, cursor position x:{x}, y:{y} \n{result.output}",
            base64_image=result.base64_image,
        )

    async def left_click_drag(self, x, y, take_screenshot=True) -> ToolResult:
        pyautogui.dragTo(x, y, self._mouse_move_duration, button="left", mouseDownUp=True)
        await asyncio.sleep(self._screenshot_delay)
        result = await self._delay_screenshot(take_screenshot)
        return ToolResult(output=f"cursor position x:{x}, y:{y}", base64_image=result.base64_image)

    async def click(self, action: str, take_screenshot=True) -> ToolResult:
        """Handle mouse clicks using platform-appropriate method."""
        if platform.system() == "Darwin":
            # Map actions to pyautogui functions
            action_map = {
                "left_click": lambda: pyautogui.click(button="left"),
                "right_click": lambda: pyautogui.click(button="right"),
                "middle_click": lambda: pyautogui.click(button="middle"),
                "double_click": lambda: pyautogui.click(clicks=2, interval=0.5),
            }

            if action not in action_map:
                raise ToolError(f"Unsupported mouse action: {action}")

            action_map[action]()
            time.sleep(0.1)
            result = await self._delay_screenshot(take_screenshot)
            return ToolResult(
                output=f"Performed {action} successfully, check the following screenshot for verification. \n{result.output}",
                base64_image=result.base64_image,
            )
        else:
            click_arg = {
                "left_click": "1",
                "right_click": "3",
                "middle_click": "2",
                "double_click": "--repeat 2 --delay 500 1",
            }[action]
            return await self.shell(f"{self.xdotool} click {click_arg}")
