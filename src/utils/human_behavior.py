"""
Human-like Behavior Simulation
==============================

Simulates human-like interactions to avoid bot detection.
Includes realistic typing, mouse movements, scrolling, and delays.
"""

import asyncio
import random
import math
from typing import Optional, Tuple, List
from dataclasses import dataclass

from playwright.async_api import Page, Locator, ElementHandle

from src.utils.logger import get_logger


@dataclass
class HumanBehaviorConfig:
    """Configuration for human behavior simulation."""

    # Typing configuration
    typing_speed_min: int = 50   # ms between keystrokes (fast typer)
    typing_speed_max: int = 150  # ms between keystrokes (slow typer)
    typo_probability: float = 0.02  # 2% chance of typo
    pause_probability: float = 0.05  # 5% chance of brief pause while typing

    # Mouse movement configuration
    mouse_speed: float = 1.0  # Multiplier for mouse movement speed
    mouse_jitter: int = 3  # Random pixel jitter on clicks

    # Delay configuration
    action_delay_min: int = 100   # ms minimum delay between actions
    action_delay_max: int = 500   # ms maximum delay between actions
    think_delay_min: int = 500    # ms minimum "thinking" delay
    think_delay_max: int = 2000   # ms maximum "thinking" delay

    # Scroll configuration
    scroll_speed_min: int = 100  # pixels per scroll step
    scroll_speed_max: int = 300  # pixels per scroll step


class HumanBehavior:
    """
    Simulates human-like behavior for browser automation.

    Provides methods for realistic typing, clicking, scrolling,
    and other interactions that mimic human behavior patterns.
    """

    def __init__(
        self,
        page: Page,
        config: Optional[HumanBehaviorConfig] = None,
    ):
        """
        Initialize human behavior simulator.

        Args:
            page: Playwright page instance.
            config: Optional behavior configuration.
        """
        self.page = page
        self.config = config or HumanBehaviorConfig()
        self.log = get_logger("HumanBehavior")
        self._last_mouse_position: Tuple[int, int] = (0, 0)

    async def type_like_human(
        self,
        locator: Locator,
        text: str,
        clear_first: bool = True,
    ) -> None:
        """
        Type text with human-like timing and occasional corrections.

        Args:
            locator: Element to type into.
            text: Text to type.
            clear_first: Whether to clear the field first.
        """
        self.log.debug(f"Human typing: {text[:20]}...")

        # Focus and clear if needed
        await locator.click()
        await self.random_delay(100, 300)

        if clear_first:
            await locator.fill("")
            await self.random_delay(50, 150)

        # Type character by character with human-like timing
        i = 0
        while i < len(text):
            char = text[i]

            # Simulate occasional typo and correction
            if (
                self.config.typo_probability > 0
                and random.random() < self.config.typo_probability
                and i < len(text) - 1
            ):
                # Make a typo
                wrong_char = self._get_nearby_key(char)
                if wrong_char != char:
                    await locator.press(wrong_char)
                    await self.random_delay(50, 150)
                    # Realize mistake and correct
                    await self.random_delay(200, 500)  # "Notice" the mistake
                    await locator.press("Backspace")
                    await self.random_delay(50, 100)

            # Type the correct character
            await locator.press(char)

            # Variable delay between keystrokes
            delay = random.randint(
                self.config.typing_speed_min,
                self.config.typing_speed_max,
            )

            # Occasional pause (like thinking)
            if random.random() < self.config.pause_probability:
                delay += random.randint(200, 800)

            await asyncio.sleep(delay / 1000)
            i += 1

    async def click_like_human(
        self,
        locator: Locator,
        move_mouse: bool = True,
    ) -> None:
        """
        Click an element with human-like behavior.

        Args:
            locator: Element to click.
            move_mouse: Whether to simulate mouse movement.
        """
        # Get element bounding box
        box = await locator.bounding_box()
        if not box:
            # Fallback to regular click
            await locator.click()
            return

        # Calculate click position with slight randomization
        # Humans don't click exactly in the center
        jitter = self.config.mouse_jitter
        target_x = box["x"] + box["width"] / 2 + random.randint(-jitter, jitter)
        target_y = box["y"] + box["height"] / 2 + random.randint(-jitter, jitter)

        # Ensure click is within bounds
        target_x = max(box["x"] + 5, min(target_x, box["x"] + box["width"] - 5))
        target_y = max(box["y"] + 5, min(target_y, box["y"] + box["height"] - 5))

        if move_mouse:
            # Move mouse in a natural curve
            await self._move_mouse_naturally(int(target_x), int(target_y))

        # Small delay before clicking (human reaction time)
        await self.random_delay(50, 150)

        # Click
        await self.page.mouse.click(target_x, target_y)
        self._last_mouse_position = (int(target_x), int(target_y))

        self.log.debug(f"Human click at ({target_x:.0f}, {target_y:.0f})")

    async def scroll_like_human(
        self,
        direction: str = "down",
        amount: int = 300,
    ) -> None:
        """
        Scroll the page with human-like behavior.

        Args:
            direction: 'up' or 'down'.
            amount: Total pixels to scroll.
        """
        scrolled = 0
        sign = -1 if direction == "down" else 1

        while scrolled < amount:
            # Variable scroll amount
            step = random.randint(
                self.config.scroll_speed_min,
                self.config.scroll_speed_max,
            )
            step = min(step, amount - scrolled)

            await self.page.mouse.wheel(0, sign * step)
            scrolled += step

            # Variable delay between scroll steps
            await self.random_delay(30, 100)

        self.log.debug(f"Scrolled {direction} {amount}px")

    async def random_delay(
        self,
        min_ms: Optional[int] = None,
        max_ms: Optional[int] = None,
    ) -> None:
        """
        Wait for a random duration.

        Args:
            min_ms: Minimum delay in milliseconds.
            max_ms: Maximum delay in milliseconds.
        """
        min_ms = min_ms or self.config.action_delay_min
        max_ms = max_ms or self.config.action_delay_max
        delay = random.randint(min_ms, max_ms)
        await asyncio.sleep(delay / 1000)

    async def think_delay(self) -> None:
        """Simulate a 'thinking' pause, longer than action delay."""
        delay = random.randint(
            self.config.think_delay_min,
            self.config.think_delay_max,
        )
        self.log.debug(f"Thinking pause: {delay}ms")
        await asyncio.sleep(delay / 1000)

    async def random_mouse_movement(self) -> None:
        """Make a random mouse movement to simulate human activity."""
        viewport = self.page.viewport_size
        if not viewport:
            return

        # Random position within viewport
        x = random.randint(100, viewport["width"] - 100)
        y = random.randint(100, viewport["height"] - 100)

        await self._move_mouse_naturally(x, y)

    async def _move_mouse_naturally(
        self,
        target_x: int,
        target_y: int,
    ) -> None:
        """
        Move mouse in a natural curve using Bezier interpolation.

        Args:
            target_x: Target X coordinate.
            target_y: Target Y coordinate.
        """
        start_x, start_y = self._last_mouse_position

        # If starting from (0,0), set a reasonable start position
        if start_x == 0 and start_y == 0:
            viewport = self.page.viewport_size
            if viewport:
                start_x = viewport["width"] // 2
                start_y = viewport["height"] // 2

        # Calculate distance
        distance = math.sqrt((target_x - start_x) ** 2 + (target_y - start_y) ** 2)

        # Number of steps based on distance
        steps = max(5, int(distance / 50))

        # Generate control points for Bezier curve
        # Add some randomness to make it look natural
        ctrl1_x = start_x + (target_x - start_x) * 0.3 + random.randint(-50, 50)
        ctrl1_y = start_y + (target_y - start_y) * 0.3 + random.randint(-50, 50)
        ctrl2_x = start_x + (target_x - start_x) * 0.7 + random.randint(-50, 50)
        ctrl2_y = start_y + (target_y - start_y) * 0.7 + random.randint(-50, 50)

        # Move along the curve
        for i in range(steps + 1):
            t = i / steps

            # Cubic Bezier formula
            x = (
                (1 - t) ** 3 * start_x
                + 3 * (1 - t) ** 2 * t * ctrl1_x
                + 3 * (1 - t) * t ** 2 * ctrl2_x
                + t ** 3 * target_x
            )
            y = (
                (1 - t) ** 3 * start_y
                + 3 * (1 - t) ** 2 * t * ctrl1_y
                + 3 * (1 - t) * t ** 2 * ctrl2_y
                + t ** 3 * target_y
            )

            await self.page.mouse.move(x, y)

            # Variable speed (faster in middle, slower at ends)
            speed_factor = 1.0 - 0.5 * math.sin(math.pi * t)
            delay = int(10 * speed_factor / self.config.mouse_speed)
            await asyncio.sleep(delay / 1000)

        self._last_mouse_position = (target_x, target_y)

    def _get_nearby_key(self, char: str) -> str:
        """Get a nearby key on the keyboard for typo simulation."""
        # Simplified keyboard layout for common typos
        keyboard_neighbors = {
            'a': ['s', 'q', 'z'],
            'b': ['v', 'n', 'g', 'h'],
            'c': ['x', 'v', 'd', 'f'],
            'd': ['s', 'f', 'e', 'r', 'c', 'x'],
            'e': ['w', 'r', 'd', 's'],
            'f': ['d', 'g', 'r', 't', 'v', 'c'],
            'g': ['f', 'h', 't', 'y', 'b', 'v'],
            'h': ['g', 'j', 'y', 'u', 'n', 'b'],
            'i': ['u', 'o', 'k', 'j'],
            'j': ['h', 'k', 'u', 'i', 'm', 'n'],
            'k': ['j', 'l', 'i', 'o', 'm'],
            'l': ['k', 'o', 'p'],
            'm': ['n', 'j', 'k'],
            'n': ['b', 'm', 'h', 'j'],
            'o': ['i', 'p', 'k', 'l'],
            'p': ['o', 'l'],
            'q': ['w', 'a'],
            'r': ['e', 't', 'd', 'f'],
            's': ['a', 'd', 'w', 'e', 'x', 'z'],
            't': ['r', 'y', 'f', 'g'],
            'u': ['y', 'i', 'h', 'j'],
            'v': ['c', 'b', 'f', 'g'],
            'w': ['q', 'e', 'a', 's'],
            'x': ['z', 'c', 's', 'd'],
            'y': ['t', 'u', 'g', 'h'],
            'z': ['a', 'x', 's'],
            '0': ['9', '-'],
            '1': ['2', 'q'],
            '2': ['1', '3', 'q', 'w'],
            '3': ['2', '4', 'w', 'e'],
            '4': ['3', '5', 'e', 'r'],
            '5': ['4', '6', 'r', 't'],
            '6': ['5', '7', 't', 'y'],
            '7': ['6', '8', 'y', 'u'],
            '8': ['7', '9', 'u', 'i'],
            '9': ['8', '0', 'i', 'o'],
        }

        char_lower = char.lower()
        if char_lower in keyboard_neighbors:
            nearby = random.choice(keyboard_neighbors[char_lower])
            return nearby.upper() if char.isupper() else nearby

        return char  # Return original if no neighbors defined

    async def simulate_reading(self, duration_ms: int = 2000) -> None:
        """
        Simulate a user reading content on the page.

        Args:
            duration_ms: Approximate time to "read" in milliseconds.
        """
        # Vary the actual reading time
        actual_duration = duration_ms + random.randint(-500, 500)
        actual_duration = max(500, actual_duration)

        # Occasionally move mouse while "reading"
        segments = random.randint(1, 3)
        segment_duration = actual_duration / segments

        for _ in range(segments):
            await asyncio.sleep(segment_duration / 1000)
            if random.random() < 0.3:  # 30% chance of mouse movement
                await self.random_mouse_movement()

        self.log.debug(f"Simulated reading for {actual_duration}ms")

    async def fill_form_field(
        self,
        locator: Locator,
        value: str,
        pre_delay: bool = True,
    ) -> None:
        """
        Fill a form field with human-like behavior.

        Args:
            locator: Form field locator.
            value: Value to fill.
            pre_delay: Whether to add a delay before filling.
        """
        if pre_delay:
            await self.think_delay()

        # Click the field first
        await self.click_like_human(locator)
        await self.random_delay(100, 300)

        # Type the value
        await self.type_like_human(locator, value)

        # Tab out or click elsewhere to trigger validation
        await self.random_delay(100, 200)


def create_human_behavior(
    page: Page,
    config: Optional[HumanBehaviorConfig] = None,
) -> HumanBehavior:
    """
    Create a HumanBehavior instance for a page.

    Args:
        page: Playwright page instance.
        config: Optional behavior configuration.

    Returns:
        HumanBehavior instance.
    """
    return HumanBehavior(page, config)
