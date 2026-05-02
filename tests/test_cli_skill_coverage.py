"""Coverage tests for src/pretorin/cli/skill.py.

Covers `pretorin skill install/uninstall/status/list-agents` plus the
internal helpers (_skill_source, _resolve_target, _resolve_targets,
_install_to, _uninstall_from, _is_installed_at).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from pretorin.cli import skill as skill_mod
from pretorin.cli.main import app
from pretorin.cli.output import set_json_mode

runner = CliRunner()


@pytest.fixture(autouse=True)
def _reset_json_mode():
    set_json_mode(False)
    yield
    set_json_mode(False)


@pytest.fixture
def fake_skill_source(tmp_path: Path) -> Path:
    """Create a minimal skill source directory under tmp_path."""
    source = tmp_path / "skill-source"
    source.mkdir()
    (source / "SKILL.md").write_text("# Pretorin skill\n")
    (source / "references").mkdir()
    (source / "references" / "tools.md").write_text("# tools\n")
    return source


# ---------------------------------------------------------------------------
# _skill_source
# ---------------------------------------------------------------------------


class TestSkillSource:
    def test_returns_pkg_path_when_skill_data_exists(self, tmp_path: Path) -> None:
        """When skill_data/SKILL.md exists inside the package, that path wins."""
        fake_pkg = tmp_path / "pretorin"
        fake_pkg.mkdir()
        skill_data = fake_pkg / "skill_data"
        skill_data.mkdir()
        (skill_data / "SKILL.md").write_text("# wheel skill\n")
        fake_module_file = fake_pkg / "cli" / "skill.py"
        fake_module_file.parent.mkdir(parents=True)
        fake_module_file.write_text("")

        with patch.object(skill_mod, "__file__", str(fake_module_file)):
            result = skill_mod._skill_source()
        assert result == skill_data

    def test_falls_back_to_repo_path_when_pkg_path_missing(self, tmp_path: Path) -> None:
        """In editable installs, falls back to the repo-root pretorin-skill/ dir."""
        # Layout: tmp_path/pretorin/cli/skill.py and tmp_path/pretorin-skill/SKILL.md
        # (skill_source walks up four levels from skill.py)
        repo_root = tmp_path
        pkg_dir = repo_root / "src" / "pretorin"
        cli_dir = pkg_dir / "cli"
        cli_dir.mkdir(parents=True)
        fake_module_file = cli_dir / "skill.py"
        fake_module_file.write_text("")

        repo_skill = repo_root / "pretorin-skill"
        repo_skill.mkdir()
        (repo_skill / "SKILL.md").write_text("# repo skill\n")

        with patch.object(skill_mod, "__file__", str(fake_module_file)):
            result = skill_mod._skill_source()
        assert result == repo_skill

    def test_falls_through_when_neither_path_exists(self, tmp_path: Path) -> None:
        """When nothing exists, returns the pkg path so _install_to can surface a clear error."""
        empty_root = tmp_path / "empty"
        cli_dir = empty_root / "src" / "pretorin" / "cli"
        cli_dir.mkdir(parents=True)
        fake_module_file = cli_dir / "skill.py"
        fake_module_file.write_text("")

        with patch.object(skill_mod, "__file__", str(fake_module_file)):
            result = skill_mod._skill_source()
        # Pkg path: <module>/../../skill_data → pretorin/skill_data
        assert result == empty_root / "src" / "pretorin" / "skill_data"


# ---------------------------------------------------------------------------
# _resolve_target / _is_installed_at
# ---------------------------------------------------------------------------


class TestResolveTarget:
    def test_claude_target_under_home(self, tmp_path: Path) -> None:
        with patch.object(Path, "home", return_value=tmp_path):
            target = skill_mod._resolve_target("claude")
        assert target == tmp_path / ".claude" / "skills" / "pretorin"

    def test_codex_target_under_home(self, tmp_path: Path) -> None:
        with patch.object(Path, "home", return_value=tmp_path):
            target = skill_mod._resolve_target("codex")
        assert target == tmp_path / ".codex" / "skills" / "pretorin"

    def test_unknown_agent_raises_keyerror(self) -> None:
        with pytest.raises(KeyError):
            skill_mod._resolve_target("nonexistent")


class TestIsInstalledAt:
    def test_returns_true_when_skill_md_exists(self, tmp_path: Path) -> None:
        target = tmp_path / "skills"
        target.mkdir()
        (target / "SKILL.md").write_text("ok")
        assert skill_mod._is_installed_at(target) is True

    def test_returns_false_when_skill_md_missing(self, tmp_path: Path) -> None:
        target = tmp_path / "empty"
        target.mkdir()
        assert skill_mod._is_installed_at(target) is False

    def test_returns_false_when_target_missing(self, tmp_path: Path) -> None:
        assert skill_mod._is_installed_at(tmp_path / "does-not-exist") is False


# ---------------------------------------------------------------------------
# _install_to
# ---------------------------------------------------------------------------


class TestInstallTo:
    def test_install_succeeds_when_target_does_not_exist(
        self, tmp_path: Path, fake_skill_source: Path
    ) -> None:
        target = tmp_path / "claude-skills" / "pretorin"
        with patch.object(skill_mod, "_skill_source", return_value=fake_skill_source):
            ok, msg = skill_mod._install_to(target)
        assert ok is True
        assert msg == str(target)
        assert (target / "SKILL.md").exists()
        assert (target / "references" / "tools.md").exists()

    def test_install_fails_when_source_missing(self, tmp_path: Path) -> None:
        empty_source = tmp_path / "missing-source"
        empty_source.mkdir()
        with patch.object(skill_mod, "_skill_source", return_value=empty_source):
            ok, msg = skill_mod._install_to(tmp_path / "target")
        assert ok is False
        assert "Bundled skill data not found" in msg

    def test_install_refuses_overwrite_without_force(
        self, tmp_path: Path, fake_skill_source: Path
    ) -> None:
        target = tmp_path / "existing"
        target.mkdir()
        (target / "marker").write_text("existing")
        with patch.object(skill_mod, "_skill_source", return_value=fake_skill_source):
            ok, msg = skill_mod._install_to(target, force=False)
        assert ok is False
        assert "Already installed" in msg
        assert "--force" in msg
        # Original content untouched
        assert (target / "marker").exists()

    def test_install_overwrites_with_force(self, tmp_path: Path, fake_skill_source: Path) -> None:
        target = tmp_path / "existing"
        target.mkdir()
        (target / "marker").write_text("old")
        with patch.object(skill_mod, "_skill_source", return_value=fake_skill_source):
            ok, msg = skill_mod._install_to(target, force=True)
        assert ok is True
        assert msg == str(target)
        assert not (target / "marker").exists()
        assert (target / "SKILL.md").exists()


# ---------------------------------------------------------------------------
# _uninstall_from
# ---------------------------------------------------------------------------


class TestUninstallFrom:
    def test_uninstall_removes_directory(self, tmp_path: Path) -> None:
        target = tmp_path / "installed"
        target.mkdir()
        (target / "SKILL.md").write_text("ok")
        ok, msg = skill_mod._uninstall_from(target)
        assert ok is True
        assert msg == str(target)
        assert not target.exists()

    def test_uninstall_returns_false_when_missing(self, tmp_path: Path) -> None:
        ok, msg = skill_mod._uninstall_from(tmp_path / "never-installed")
        assert ok is False
        assert msg == "Not installed."


# ---------------------------------------------------------------------------
# _resolve_targets
# ---------------------------------------------------------------------------


class TestResolveTargets:
    def test_default_returns_all_known_agents(self, tmp_path: Path) -> None:
        with patch.object(Path, "home", return_value=tmp_path):
            results = skill_mod._resolve_targets(None, None)
        labels = [label for label, _ in results]
        assert set(labels) == set(skill_mod.KNOWN_AGENTS.keys())

    def test_explicit_agents_subset(self, tmp_path: Path) -> None:
        with patch.object(Path, "home", return_value=tmp_path):
            results = skill_mod._resolve_targets(["claude"], None)
        assert results == [("claude", tmp_path / ".claude" / "skills" / "pretorin")]

    def test_explicit_path_appends_skill_name(self, tmp_path: Path) -> None:
        custom = tmp_path / "my-skills-dir"
        results = skill_mod._resolve_targets(None, custom)
        assert len(results) == 1
        _label, target = results[0]
        assert target == custom / skill_mod.SKILL_NAME

    def test_explicit_path_already_named_pretorin_used_as_is(self, tmp_path: Path) -> None:
        custom = tmp_path / "container" / "pretorin"
        results = skill_mod._resolve_targets(None, custom)
        _label, target = results[0]
        assert target == custom

    def test_unknown_agent_exits_1(self) -> None:
        result = runner.invoke(app, ["skill", "install", "--agent", "definitely-not-real"])
        assert result.exit_code == 1
        assert "Unknown agent" in result.output


# ---------------------------------------------------------------------------
# `pretorin skill install`
# ---------------------------------------------------------------------------


class TestInstallCommand:
    def test_install_default_writes_to_all_known_agents(
        self, tmp_path: Path, fake_skill_source: Path
    ) -> None:
        with (
            patch.object(Path, "home", return_value=tmp_path),
            patch.object(skill_mod, "_skill_source", return_value=fake_skill_source),
        ):
            result = runner.invoke(app, ["skill", "install"])
        assert result.exit_code == 0
        for agent in skill_mod.KNOWN_AGENTS:
            target = skill_mod._resolve_target(agent)
            assert (target / "SKILL.md").exists()

    def test_install_specific_agent(self, tmp_path: Path, fake_skill_source: Path) -> None:
        with (
            patch.object(Path, "home", return_value=tmp_path),
            patch.object(skill_mod, "_skill_source", return_value=fake_skill_source),
        ):
            result = runner.invoke(app, ["skill", "install", "--agent", "claude"])
        assert result.exit_code == 0
        assert (tmp_path / ".claude" / "skills" / "pretorin" / "SKILL.md").exists()
        assert not (tmp_path / ".codex" / "skills" / "pretorin").exists()

    def test_install_existing_without_force_reports_warning(
        self, tmp_path: Path, fake_skill_source: Path
    ) -> None:
        with (
            patch.object(Path, "home", return_value=tmp_path),
            patch.object(skill_mod, "_skill_source", return_value=fake_skill_source),
        ):
            first = runner.invoke(app, ["skill", "install", "--agent", "claude"])
            assert first.exit_code == 0
            second = runner.invoke(app, ["skill", "install", "--agent", "claude"])
        assert second.exit_code == 0
        assert "Already installed" in second.output

    def test_install_force_overwrites(self, tmp_path: Path, fake_skill_source: Path) -> None:
        with (
            patch.object(Path, "home", return_value=tmp_path),
            patch.object(skill_mod, "_skill_source", return_value=fake_skill_source),
        ):
            first = runner.invoke(app, ["skill", "install", "--agent", "claude"])
            assert first.exit_code == 0
            forced = runner.invoke(app, ["skill", "install", "--agent", "claude", "--force"])
        assert forced.exit_code == 0
        assert (tmp_path / ".claude" / "skills" / "pretorin" / "SKILL.md").exists()

    def test_install_custom_path(self, tmp_path: Path, fake_skill_source: Path) -> None:
        custom = tmp_path / "custom-skills"
        with patch.object(skill_mod, "_skill_source", return_value=fake_skill_source):
            result = runner.invoke(app, ["skill", "install", "--path", str(custom)])
        assert result.exit_code == 0
        assert (custom / "pretorin" / "SKILL.md").exists()

    def test_install_json_mode_returns_status_per_agent(
        self, tmp_path: Path, fake_skill_source: Path
    ) -> None:
        with (
            patch.object(Path, "home", return_value=tmp_path),
            patch.object(skill_mod, "_skill_source", return_value=fake_skill_source),
        ):
            result = runner.invoke(app, ["--json", "skill", "install"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert "claude" in payload
        assert "codex" in payload
        assert payload["claude"]["installed"] is True
        assert payload["codex"]["installed"] is True


# ---------------------------------------------------------------------------
# `pretorin skill uninstall`
# ---------------------------------------------------------------------------


class TestUninstallCommand:
    def test_uninstall_removes_installed_skill(
        self, tmp_path: Path, fake_skill_source: Path
    ) -> None:
        with (
            patch.object(Path, "home", return_value=tmp_path),
            patch.object(skill_mod, "_skill_source", return_value=fake_skill_source),
        ):
            installed = runner.invoke(app, ["skill", "install", "--agent", "claude"])
            assert installed.exit_code == 0
            removed = runner.invoke(app, ["skill", "uninstall", "--agent", "claude"])
        assert removed.exit_code == 0
        assert not (tmp_path / ".claude" / "skills" / "pretorin").exists()

    def test_uninstall_when_not_installed_is_quiet(self, tmp_path: Path) -> None:
        with patch.object(Path, "home", return_value=tmp_path):
            result = runner.invoke(app, ["skill", "uninstall", "--agent", "claude"])
        assert result.exit_code == 0
        assert "Not installed" in result.output

    def test_uninstall_json_mode(self, tmp_path: Path, fake_skill_source: Path) -> None:
        with (
            patch.object(Path, "home", return_value=tmp_path),
            patch.object(skill_mod, "_skill_source", return_value=fake_skill_source),
        ):
            runner.invoke(app, ["skill", "install", "--agent", "claude"])
            result = runner.invoke(app, ["--json", "skill", "uninstall", "--agent", "claude"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["claude"]["uninstalled"] is True


# ---------------------------------------------------------------------------
# `pretorin skill status`
# ---------------------------------------------------------------------------


class TestStatusCommand:
    def test_status_table_mode_shows_each_agent(self, tmp_path: Path) -> None:
        with patch.object(Path, "home", return_value=tmp_path):
            result = runner.invoke(app, ["skill", "status"])
        assert result.exit_code == 0
        for agent in skill_mod.KNOWN_AGENTS:
            assert agent.capitalize() in result.output

    def test_status_table_marks_installed_agent(
        self, tmp_path: Path, fake_skill_source: Path
    ) -> None:
        with (
            patch.object(Path, "home", return_value=tmp_path),
            patch.object(skill_mod, "_skill_source", return_value=fake_skill_source),
        ):
            runner.invoke(app, ["skill", "install", "--agent", "claude"])
            result = runner.invoke(app, ["skill", "status"])
        assert result.exit_code == 0
        assert "installed" in result.output

    def test_status_json_mode(self, tmp_path: Path, fake_skill_source: Path) -> None:
        with (
            patch.object(Path, "home", return_value=tmp_path),
            patch.object(skill_mod, "_skill_source", return_value=fake_skill_source),
        ):
            runner.invoke(app, ["skill", "install", "--agent", "claude"])
            result = runner.invoke(app, ["--json", "skill", "status"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["claude"]["installed"] is True
        assert payload["codex"]["installed"] is False
        assert "path" in payload["claude"]


# ---------------------------------------------------------------------------
# `pretorin skill list-agents`
# ---------------------------------------------------------------------------


class TestListAgentsCommand:
    def test_list_agents_table_mode(self, tmp_path: Path) -> None:
        with patch.object(Path, "home", return_value=tmp_path):
            result = runner.invoke(app, ["skill", "list-agents"])
        assert result.exit_code == 0
        for agent in skill_mod.KNOWN_AGENTS:
            assert agent in result.output

    def test_list_agents_json_mode(self, tmp_path: Path) -> None:
        with patch.object(Path, "home", return_value=tmp_path):
            result = runner.invoke(app, ["--json", "skill", "list-agents"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert set(payload.keys()) == set(skill_mod.KNOWN_AGENTS.keys())
        # Each value should be a string path
        for value in payload.values():
            assert isinstance(value, str)
