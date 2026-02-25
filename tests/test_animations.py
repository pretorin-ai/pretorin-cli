"""Tests for Rome-bot ASCII animations module."""

from unittest.mock import MagicMock, patch

from pretorin.cli.animations import (
    ANIMATION_FRAMES,
    FRAME_RATES,
    MARCHING_FRAMES,
    ROMEBOT_COLOR,
    SEARCHING_FRAMES,
    THINKING_FRAMES,
    AnimationFrame,
    AnimationTheme,
    RomebotSpinner,
    animated_status,
    supports_animation,
)


class TestAnimationFrame:
    """Tests for the AnimationFrame dataclass."""

    def test_animation_frame_creation(self):
        """Test creating an animation frame."""
        frame = AnimationFrame(lines=["  ∫  ", "[°~°]"])
        assert len(frame.lines) == 2
        assert "[°~°]" in frame.lines[1]

    def test_animation_frame_render(self):
        """Test rendering an animation frame."""
        frame = AnimationFrame(lines=["  ∫  ", "[°~°]"])
        text = frame.render("Loading...")
        plain = text.plain
        assert "∫" in plain
        assert "[°~°]" in plain
        assert "Loading..." in plain

    def test_animation_frame_render_no_message(self):
        """Test rendering an animation frame without message."""
        frame = AnimationFrame(lines=["  ∫  ", "[°~°]"])
        text = frame.render()
        plain = text.plain
        assert "∫" in plain
        assert "[°~°]" in plain


class TestAnimationTheme:
    """Tests for animation themes."""

    def test_animation_theme_values(self):
        """Test that all expected themes exist."""
        assert AnimationTheme.MARCHING.value == "marching"
        assert AnimationTheme.SEARCHING.value == "searching"
        assert AnimationTheme.THINKING.value == "thinking"

    def test_all_themes_have_frames(self):
        """Test that all themes have associated frames."""
        for theme in AnimationTheme:
            assert theme in ANIMATION_FRAMES
            assert len(ANIMATION_FRAMES[theme]) >= 2

    def test_all_themes_have_frame_rates(self):
        """Test that all themes have frame rates."""
        for theme in AnimationTheme:
            assert theme in FRAME_RATES
            assert isinstance(FRAME_RATES[theme], float)
            assert FRAME_RATES[theme] > 0


class TestAnimationFrames:
    """Tests for the pre-defined animation frames."""

    def test_marching_frames_count(self):
        """Test marching animation has 4 frames."""
        assert len(MARCHING_FRAMES) == 4

    def test_searching_frames_count(self):
        """Test searching animation has 4 frames."""
        assert len(SEARCHING_FRAMES) == 4

    def test_thinking_frames_count(self):
        """Test thinking animation has 4 frames."""
        assert len(THINKING_FRAMES) == 4

    def test_all_frames_have_romebot_face(self):
        """Test all animation frames contain Rome-bot face."""
        all_frames = MARCHING_FRAMES + SEARCHING_FRAMES + THINKING_FRAMES
        for frame in all_frames:
            frame_text = "\n".join(frame.lines)
            assert "[°~°]" in frame_text

    def test_all_frames_have_helmet(self):
        """Test all animation frames contain Rome-bot helmet."""
        all_frames = MARCHING_FRAMES + SEARCHING_FRAMES + THINKING_FRAMES
        for frame in all_frames:
            frame_text = "\n".join(frame.lines)
            assert "∫" in frame_text

    def test_searching_frames_have_lantern(self):
        """Test searching frames contain the lantern 'o'."""
        for frame in SEARCHING_FRAMES:
            frame_text = "\n".join(frame.lines)
            assert "o" in frame_text

    def test_thinking_frames_have_question_mark(self):
        """Test at least some thinking frames have question mark."""
        has_question = any(
            "?" in "\n".join(frame.lines)
            for frame in THINKING_FRAMES
        )
        assert has_question


class TestSupportsAnimation:
    """Tests for terminal capability detection."""

    def test_supports_animation_tty(self):
        """Test animation supported when stdout is TTY."""
        with patch("sys.stdout.isatty", return_value=True):
            assert supports_animation() is True

    def test_supports_animation_no_tty(self):
        """Test animation not supported when stdout is not TTY."""
        with patch("sys.stdout.isatty", return_value=False):
            assert supports_animation() is False


class TestRomebotSpinner:
    """Tests for the RomebotSpinner class."""

    def test_spinner_creation(self):
        """Test creating a spinner."""
        spinner = RomebotSpinner("Loading...", AnimationTheme.MARCHING)
        assert spinner.message == "Loading..."
        assert spinner.theme == AnimationTheme.MARCHING
        assert spinner.current_frame == 0

    def test_spinner_frame_rate_matches_theme(self):
        """Test spinner uses correct frame rate for theme."""
        for theme in AnimationTheme:
            spinner = RomebotSpinner("Test", theme)
            assert spinner.frame_rate == FRAME_RATES[theme]

    def test_spinner_context_manager_no_tty(self):
        """Test spinner context manager works without TTY."""
        with patch("pretorin.cli.animations.supports_animation", return_value=False):
            mock_console = MagicMock()
            spinner = RomebotSpinner("Loading...", AnimationTheme.MARCHING, console=mock_console)

            with spinner:
                pass

            # Should print static fallback
            mock_console.print.assert_called_once()


class TestAnimatedStatus:
    """Tests for the animated_status context manager."""

    def test_animated_status_no_tty(self):
        """Test animated_status works without TTY (fallback mode)."""
        with patch("pretorin.cli.animations.supports_animation", return_value=False):
            mock_console = MagicMock()

            with animated_status("Loading...", AnimationTheme.MARCHING, console=mock_console) as spinner:
                assert isinstance(spinner, RomebotSpinner)

            # Should have printed the fallback message
            mock_console.print.assert_called()

    def test_animated_status_default_theme(self):
        """Test animated_status uses MARCHING theme by default."""
        with patch("pretorin.cli.animations.supports_animation", return_value=False):
            mock_console = MagicMock()

            with animated_status("Loading...", console=mock_console) as spinner:
                assert spinner.theme == AnimationTheme.MARCHING

    def test_animated_status_custom_theme(self):
        """Test animated_status respects custom theme."""
        with patch("pretorin.cli.animations.supports_animation", return_value=False):
            mock_console = MagicMock()

            with animated_status("Searching...", AnimationTheme.SEARCHING, console=mock_console) as spinner:
                assert spinner.theme == AnimationTheme.SEARCHING


class TestBrandColors:
    """Tests for brand color usage."""

    def test_romebot_color_is_gold(self):
        """Test Rome-bot uses the brand gold color."""
        assert ROMEBOT_COLOR == "#EAB536"

    def test_frame_render_uses_brand_color(self):
        """Test rendered frames use the brand color styling."""
        frame = AnimationFrame(lines=["[°~°]"])
        text = frame.render()
        # The Text object should have the gold style applied
        assert len(text._spans) > 0
