"""Rome-bot ASCII art animations for CLI loading states."""

from __future__ import annotations

import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from types import TracebackType

from rich.console import Console
from rich.live import Live
from rich.text import Text

# Brand color for Rome-bot
ROMEBOT_COLOR = "#EAB536"


@dataclass
class AnimationFrame:
    """A single frame of ASCII art animation."""

    lines: list[str]

    def render(self, message: str = "") -> Text:
        """Render the frame with optional message."""
        text = Text()
        for line in self.lines:
            text.append(line, style=ROMEBOT_COLOR)
            text.append("\n")
        if message:
            text.append(f" {message}", style="dim")
        return text


class AnimationTheme(Enum):
    """Available animation themes for different operations."""

    MARCHING = "marching"
    SEARCHING = "searching"
    THINKING = "thinking"


# Animation frames for each theme
MARCHING_FRAMES = [
    AnimationFrame(
        [
            "   \u222b   ",
            " [\u00b0~\u00b0] ",
            "  /|\\  ",
            "  / \\  ",
        ]
    ),
    AnimationFrame(
        [
            "   \u222b   ",
            " [\u00b0~\u00b0] ",
            "  \\|/  ",
            "  / \\  ",
        ]
    ),
    AnimationFrame(
        [
            "   \u222b   ",
            " [\u00b0~\u00b0] ",
            "  /|\\  ",
            " /  \\  ",
        ]
    ),
    AnimationFrame(
        [
            "   \u222b   ",
            " [\u00b0~\u00b0] ",
            "  \\|/  ",
            " \\  /  ",
        ]
    ),
]

SEARCHING_FRAMES = [
    AnimationFrame(
        [
            "   \u222b     ",
            " [\u00b0~\u00b0]o  ",
            "  /|    ",
            "  / \\   ",
        ]
    ),
    AnimationFrame(
        [
            "   \u222b      ",
            " [\u00b0~\u00b0] o ",
            "  /|     ",
            "  / \\    ",
        ]
    ),
    AnimationFrame(
        [
            "   \u222b       ",
            " [\u00b0~\u00b0]  o",
            "  /|      ",
            "  / \\     ",
        ]
    ),
    AnimationFrame(
        [
            "   \u222b      ",
            " [\u00b0~\u00b0] o ",
            "  /|     ",
            "  / \\    ",
        ]
    ),
]

THINKING_FRAMES = [
    AnimationFrame(
        [
            "   \u222b   ",
            " [\u00b0~\u00b0] ",
            "  /|\\  ",
            "  / \\  ",
        ]
    ),
    AnimationFrame(
        [
            "   \u222b ?  ",
            " [\u00b0~\u00b0]  ",
            "  /|\\   ",
            "  / \\   ",
        ]
    ),
    AnimationFrame(
        [
            "   \u222b ? ",
            " [\u00b0~\u00b0] ",
            "  /|\\  ",
            "  / \\  ",
        ]
    ),
    AnimationFrame(
        [
            "   \u222b   ",
            " [\u00b0~\u00b0] ",
            "  /|\\  ",
            "  / \\  ",
        ]
    ),
]

# Map themes to their frames
ANIMATION_FRAMES: dict[AnimationTheme, list[AnimationFrame]] = {
    AnimationTheme.MARCHING: MARCHING_FRAMES,
    AnimationTheme.SEARCHING: SEARCHING_FRAMES,
    AnimationTheme.THINKING: THINKING_FRAMES,
}

# Frame rates per theme (seconds per frame)
FRAME_RATES: dict[AnimationTheme, float] = {
    AnimationTheme.MARCHING: 0.2,
    AnimationTheme.SEARCHING: 0.25,
    AnimationTheme.THINKING: 0.4,
}


def supports_animation() -> bool:
    """Check if the terminal supports animations.

    Returns False for non-TTY environments (pipes, CI, etc.)
    """
    return sys.stdout.isatty()


class RomebotSpinner:
    """Animated Rome-bot spinner using Rich's Live display."""

    def __init__(
        self,
        message: str,
        theme: AnimationTheme = AnimationTheme.MARCHING,
        console: Console | None = None,
    ):
        self.message = message
        self.theme = theme
        self.console = console or Console()
        self.frames = ANIMATION_FRAMES[theme]
        self.frame_rate = FRAME_RATES[theme]
        self.current_frame = 0
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._live: Live | None = None

    def _advance_frame(self) -> None:
        """Advance to the next animation frame in a background thread."""
        while not self._stop_event.is_set():
            if self._live:
                frame = self.frames[self.current_frame]
                self._live.update(frame.render(self.message))
                self.current_frame = (self.current_frame + 1) % len(self.frames)
            self._stop_event.wait(self.frame_rate)

    def __enter__(self) -> RomebotSpinner:
        """Start the animation."""
        if not supports_animation():
            # Fallback: just print the static thinking face
            self.console.print(f"[{ROMEBOT_COLOR}][\u00b0~\u00b0][/{ROMEBOT_COLOR}] [dim]{self.message}[/dim]")
            return self

        # Start Live display
        self._live = Live(
            self.frames[0].render(self.message),
            console=self.console,
            refresh_per_second=10,
            transient=True,
        )
        self._live.__enter__()

        # Start background thread for frame advancement
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._advance_frame, daemon=True)
        self._thread.start()

        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Stop the animation."""
        self._stop_event.set()

        if self._thread:
            self._thread.join(timeout=1.0)

        if self._live:
            self._live.__exit__(exc_type, exc_val, exc_tb)


@contextmanager
def animated_status(
    message: str,
    theme: AnimationTheme = AnimationTheme.MARCHING,
    console: Console | None = None,
) -> Iterator[RomebotSpinner]:
    """Context manager for animated Rome-bot status display.

    Provides graceful fallback to simple output for non-TTY environments.

    Args:
        message: The status message to display
        theme: The animation theme to use
        console: Optional Rich console instance

    Usage:
        with animated_status("Loading...", AnimationTheme.SEARCHING):
            result = await some_async_operation()
    """
    spinner = RomebotSpinner(message, theme, console)
    with spinner:
        yield spinner
