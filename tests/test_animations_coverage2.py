"""Additional coverage tests for src/pretorin/cli/animations.py.

Covers lines 196-201 (_advance_frame), 211-224 (__enter__ with animation),
236 (__exit__ thread join), 239 (__exit__ Live cleanup).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from pretorin.cli.animations import AnimationTheme, RomebotSpinner


class TestRomebotSpinnerAnimationMode:
    """Tests for spinner when animation is supported (TTY mode)."""

    def test_spinner_starts_and_stops_live_and_thread(self):
        """When supports_animation() is True, __enter__ starts Live + thread
        and __exit__ stops both."""
        mock_console = MagicMock()
        spinner = RomebotSpinner("Working...", AnimationTheme.MARCHING, console=mock_console)

        with (
            patch("pretorin.cli.animations.supports_animation", return_value=True),
            patch("pretorin.cli.animations.Live") as mock_live,
        ):
            mock_live_instance = MagicMock()
            mock_live.return_value = mock_live_instance

            with spinner:
                # Live.__enter__ should have been called
                mock_live_instance.__enter__.assert_called_once()
                # A background thread should be running
                assert spinner._thread is not None
                assert spinner._thread.is_alive()

            # After exiting, thread should have been joined
            assert not spinner._thread.is_alive()
            # Live.__exit__ should have been called
            mock_live_instance.__exit__.assert_called_once()

    def test_advance_frame_updates_live_display(self):
        """_advance_frame updates the Live display and cycles frames."""
        mock_console = MagicMock()
        spinner = RomebotSpinner("Searching...", AnimationTheme.SEARCHING, console=mock_console)

        with (
            patch("pretorin.cli.animations.supports_animation", return_value=True),
            patch("pretorin.cli.animations.Live") as mock_live,
        ):
            mock_live_instance = MagicMock()
            mock_live.return_value = mock_live_instance

            with spinner:
                # Let the background thread run at least one frame
                import time

                time.sleep(spinner.frame_rate * 2 + 0.05)
                # _live.update should have been called at least once
                assert mock_live_instance.update.call_count >= 1

    def test_exit_joins_thread(self):
        """__exit__ calls thread.join(timeout=1.0)."""
        mock_console = MagicMock()
        spinner = RomebotSpinner("Loading...", AnimationTheme.THINKING, console=mock_console)

        with (
            patch("pretorin.cli.animations.supports_animation", return_value=True),
            patch("pretorin.cli.animations.Live") as mock_live,
        ):
            mock_live_instance = MagicMock()
            mock_live.return_value = mock_live_instance

            spinner.__enter__()
            thread = spinner._thread
            assert thread is not None
            spinner.__exit__(None, None, None)

            # Thread should no longer be alive
            assert not thread.is_alive()

    def test_exit_without_thread_or_live(self):
        """__exit__ handles gracefully when no thread or live was started."""
        mock_console = MagicMock()
        spinner = RomebotSpinner("Test", AnimationTheme.MARCHING, console=mock_console)

        # Call __exit__ directly without __enter__ - should not raise
        spinner.__exit__(None, None, None)
        assert spinner._thread is None
        assert spinner._live is None

    def test_advance_frame_cycles_through_all_frames(self):
        """_advance_frame loops through all frames in the theme."""
        mock_console = MagicMock()
        spinner = RomebotSpinner("Cycling...", AnimationTheme.MARCHING, console=mock_console)
        spinner.frame_rate = 0.01  # Speed up for testing

        with (
            patch("pretorin.cli.animations.supports_animation", return_value=True),
            patch("pretorin.cli.animations.Live") as mock_live,
        ):
            mock_live_instance = MagicMock()
            mock_live.return_value = mock_live_instance

            with spinner:
                import time

                # Wait enough for several frame cycles
                time.sleep(0.1)

            # Frame should have advanced past the initial 0
            assert mock_live_instance.update.call_count >= 2
