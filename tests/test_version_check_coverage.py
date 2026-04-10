"""Coverage tests for src/pretorin/cli/version_check.py.

Covers lines 40-41 (_parse_version invalid), 50-51 (_load_cache invalid JSON),
61-62 (_save_cache OSError), 67-78 (_fetch_latest_version), 114 (cache fresh
failure result), 139 (latest is None after fetch), 164 (get_update_message None).
"""

from __future__ import annotations

import json
import time
from unittest.mock import MagicMock, patch

from pretorin.cli.version_check import (
    CACHE_TTL_SECONDS,
    FAILURE_CACHE_TTL_SECONDS,
    _fetch_latest_version,
    _load_cache,
    _parse_version,
    _save_cache,
    check_for_updates,
    get_update_message,
    get_update_status,
)


class TestParseVersion:
    """Tests for _parse_version."""

    def test_valid_version(self):
        assert _parse_version("1.2.3") == (1, 2, 3)

    def test_version_with_alpha_suffix(self):
        assert _parse_version("1.2.3a1") == (1, 2, 3)

    def test_version_with_beta_suffix(self):
        assert _parse_version("1.2.3b2") == (1, 2, 3)

    def test_version_with_rc_suffix(self):
        assert _parse_version("1.2.3rc1") == (1, 2, 3)

    def test_invalid_version_returns_zero_tuple(self):
        """Lines 40-41: invalid version string falls into except."""
        assert _parse_version("not.a.version") == (0, 0, 0)

    def test_empty_version_returns_zero_tuple(self):
        assert _parse_version("") == (0, 0, 0)

    def test_single_number_version(self):
        assert _parse_version("42") == (42,)


class TestLoadCache:
    """Tests for _load_cache."""

    def test_load_cache_valid_file(self, tmp_path):
        cache_file = tmp_path / ".version_cache.json"
        cache_file.write_text(json.dumps({"latest_version": "1.0.0"}))
        with patch("pretorin.cli.version_check.VERSION_CACHE_FILE", cache_file):
            result = _load_cache()
        assert result["latest_version"] == "1.0.0"

    def test_load_cache_invalid_json(self, tmp_path):
        """Lines 50-51: JSONDecodeError causes empty dict return."""
        cache_file = tmp_path / ".version_cache.json"
        cache_file.write_text("{invalid json!!!")
        with patch("pretorin.cli.version_check.VERSION_CACHE_FILE", cache_file):
            result = _load_cache()
        assert result == {}

    def test_load_cache_file_missing(self, tmp_path):
        cache_file = tmp_path / "nonexistent.json"
        with patch("pretorin.cli.version_check.VERSION_CACHE_FILE", cache_file):
            result = _load_cache()
        assert result == {}


class TestSaveCache:
    """Tests for _save_cache."""

    def test_save_cache_success(self, tmp_path):
        cache_dir = tmp_path / "cache_dir"
        cache_file = cache_dir / "cache.json"
        with patch("pretorin.cli.version_check.CACHE_DIR", cache_dir), \
             patch("pretorin.cli.version_check.VERSION_CACHE_FILE", cache_file):
            _save_cache({"latest_version": "2.0.0"})
        assert cache_file.exists()
        assert json.loads(cache_file.read_text())["latest_version"] == "2.0.0"

    def test_save_cache_os_error_silently_passes(self):
        """Lines 61-62: OSError is caught silently."""
        with patch("pretorin.cli.version_check.CACHE_DIR") as mock_dir:
            mock_dir.mkdir.side_effect = OSError("Permission denied")
            # Should not raise
            _save_cache({"latest_version": "1.0.0"})


class TestFetchLatestVersion:
    """Tests for _fetch_latest_version."""

    def test_fetch_latest_version_success(self):
        """Lines 67-78: successful PyPI fetch."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {"info": {"version": "2.0.0"}}
        ).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = _fetch_latest_version()
        assert result == "2.0.0"

    def test_fetch_latest_version_network_error(self):
        """Lines 77-78: exception returns None."""
        with patch("urllib.request.urlopen", side_effect=Exception("Network error")):
            result = _fetch_latest_version()
        assert result is None

    def test_fetch_latest_version_no_version_key(self):
        """Returns None when response lacks version."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"info": {}}).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = _fetch_latest_version()
        assert result is None


class TestCheckForUpdates:
    """Tests for check_for_updates."""

    def test_cache_fresh_with_failure_result(self, tmp_path):
        """Line 114: cached failure result returns unchecked result."""
        now = time.time()
        cache_data = {
            "last_result": "failure",
            "checked_at": now,
            "next_check_at": now + FAILURE_CACHE_TTL_SECONDS,
            "latest_version": None,
        }
        with patch("pretorin.cli.version_check._load_cache", return_value=cache_data):
            result = check_for_updates()
        assert result.checked is False
        assert result.latest_version is None
        assert result.update_available is False

    def test_latest_is_none_after_fetch(self):
        """Line 139: latest is None after falling through cache to fetch."""
        now = time.time()
        # Cache is stale (next_check_at in the past)
        cache_data = {
            "last_result": "success",
            "checked_at": now - 200000,
            "next_check_at": now - 100000,
            "latest_version": None,
        }
        with patch("pretorin.cli.version_check._load_cache", return_value=cache_data), \
             patch("pretorin.cli.version_check._fetch_latest_version", return_value=None), \
             patch("pretorin.cli.version_check._save_cache"):
            result = check_for_updates()
        assert result.checked is False
        assert result.latest_version is None

    def test_cache_fresh_success_but_no_latest_version(self):
        """Line 139: cache is fresh with success but latest_version is None."""
        now = time.time()
        cache_data = {
            "last_result": "success",
            "checked_at": now,
            "next_check_at": now + CACHE_TTL_SECONDS,
            "latest_version": None,
        }
        with patch("pretorin.cli.version_check._load_cache", return_value=cache_data):
            result = check_for_updates()
        assert result.checked is False

    def test_fetch_returns_version_saves_success(self):
        """check_for_updates with forced fetch that returns a version."""
        with patch("pretorin.cli.version_check._load_cache", return_value={}), \
             patch("pretorin.cli.version_check._fetch_latest_version", return_value="99.0.0"), \
             patch("pretorin.cli.version_check._save_cache") as mock_save:
            result = check_for_updates(force=True)
        assert result.latest_version == "99.0.0"
        assert result.update_available is True
        assert result.checked is True
        mock_save.assert_called_once()


class TestGetUpdateMessage:
    """Tests for get_update_message."""

    def test_get_update_message_none_when_disabled(self):
        """Line 164: returns None when notifications disabled."""
        with patch("pretorin.cli.version_check.update_notifications_enabled", return_value=False):
            result = get_update_message()
        assert result is None

    def test_get_update_message_none_when_no_update(self):
        """Line 164: returns None when no update is available."""
        from pretorin.cli.version_check import VersionCheckResult

        with patch("pretorin.cli.version_check.update_notifications_enabled", return_value=True), \
             patch(
                 "pretorin.cli.version_check.check_for_updates",
                 return_value=VersionCheckResult(latest_version="0.0.1", update_available=False, checked=True),
             ):
            result = get_update_message()
        assert result is None

    def test_get_update_message_returns_message_when_available(self):
        """Returns formatted message when update is available."""
        from pretorin.cli.version_check import VersionCheckResult

        with patch("pretorin.cli.version_check.update_notifications_enabled", return_value=True), \
             patch(
                 "pretorin.cli.version_check.check_for_updates",
                 return_value=VersionCheckResult(latest_version="99.0.0", update_available=True, checked=True),
             ):
            result = get_update_message()
        assert result is not None
        assert "99.0.0" in result
        assert "pip install --upgrade" in result


class TestGetUpdateStatus:
    """Tests for get_update_status."""

    def test_get_update_status_disabled(self):
        with patch("pretorin.cli.version_check.update_notifications_enabled", return_value=False):
            result = get_update_status()
        assert result["notifications_enabled"] is False
        assert result["message"] == "Passive update notifications are disabled."

    def test_get_update_status_up_to_date(self):
        from pretorin.cli.version_check import VersionCheckResult

        with patch("pretorin.cli.version_check.update_notifications_enabled", return_value=True), \
             patch(
                 "pretorin.cli.version_check.check_for_updates",
                 return_value=VersionCheckResult(latest_version="0.14.0", update_available=False, checked=True),
             ):
            result = get_update_status()
        assert result["checked"] is True
        assert result["message"] == "Pretorin CLI is up to date."
