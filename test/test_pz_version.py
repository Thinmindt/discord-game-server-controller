"""Tests for Project Zomboid version management functionality."""

import json
import pathlib
import subprocess
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from src.project_zomboid_manager import ProjectZomboidServerManager


@pytest.fixture
def temp_server_dir():
    """Create a temporary server directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        server_dir = pathlib.Path(tmpdir) / "PZServer"
        server_dir.mkdir(parents=True)
        # Create a dummy batch file
        batch_file = server_dir / "StartServer64.bat"
        batch_file.write_text("echo test")
        yield server_dir


@pytest.fixture
def manager(temp_server_dir):
    """Create a ProjectZomboidServerManager instance for testing."""
    steam_cmd = pathlib.Path("C:/steamcmd/steamcmd.exe")
    return ProjectZomboidServerManager(
        server_path=temp_server_dir,
        steam_cmd_path=steam_cmd,
        server_name="testserver",
        memory_gb=4,
    )


class TestVersionStateManagement:
    """Tests for version state file management."""

    def test_default_branch_is_stable(self, manager):
        """Test that the default branch is 'stable' when no state file exists."""
        assert manager._get_current_branch() == "stable"

    def test_server_name_stable(self, manager):
        """Test that server name is base name on stable branch."""
        assert manager.server_name == "testserver"

    def test_server_name_beta(self, manager):
        """Test that server name has _b42 suffix on beta branch."""
        manager._save_version_state("beta")
        assert manager.server_name == "testserver_b42"

    def test_save_and_load_version_state(self, manager):
        """Test saving and loading version state."""
        manager._save_version_state("beta")
        assert manager._get_current_branch() == "beta"

        manager._save_version_state("stable")
        assert manager._get_current_branch() == "stable"

    def test_version_state_file_format(self, manager):
        """Test that the version state file has the correct format."""
        manager._save_version_state("beta")

        state_path = manager._get_version_state_path()
        assert state_path.exists()

        with open(state_path) as f:
            state = json.load(f)

        assert "current_branch" in state
        assert "last_updated" in state
        assert state["current_branch"] == "beta"


class TestBranchNormalization:
    """Tests for branch name normalization."""

    def test_normalize_stable(self, manager):
        """Test normalizing 'stable' branch name."""
        assert manager._normalize_branch_name("stable") == "stable"
        assert manager._normalize_branch_name("STABLE") == "stable"
        assert manager._normalize_branch_name(" stable ") == "stable"

    def test_normalize_b41(self, manager):
        """Test normalizing 'b41' to 'stable'."""
        assert manager._normalize_branch_name("b41") == "stable"
        assert manager._normalize_branch_name("B41") == "stable"

    def test_normalize_beta(self, manager):
        """Test normalizing 'beta' branch name."""
        assert manager._normalize_branch_name("beta") == "beta"
        assert manager._normalize_branch_name("BETA") == "beta"

    def test_normalize_b42(self, manager):
        """Test normalizing 'b42' to 'beta'."""
        assert manager._normalize_branch_name("b42") == "beta"
        assert manager._normalize_branch_name("B42") == "beta"

    def test_invalid_branch_raises_error(self, manager):
        """Test that invalid branch names raise ServerControlError."""
        from src.game_server_interface import ServerControlError

        with pytest.raises(ServerControlError) as exc_info:
            manager._normalize_branch_name("invalid")

        assert "Invalid branch" in str(exc_info.value)


class TestSteamCMDCommand:
    """Tests for SteamCMD command generation."""

    def test_stable_command_no_beta_flag(self, manager):
        """Test that stable branch command has no beta flag."""
        cmd = manager._build_steamcmd_update_command("stable")

        assert "-beta" not in cmd
        assert "380870" in cmd
        assert "validate" in cmd

    def test_beta_command_has_beta_flag(self, manager):
        """Test that beta branch command has the beta flag."""
        cmd = manager._build_steamcmd_update_command("beta")

        assert "-beta" in cmd
        # Find the index of -beta and check the next element
        beta_index = cmd.index("-beta")
        assert cmd[beta_index + 1] == "unstable"
        assert "380870" in cmd
        assert "validate" in cmd


class TestGetVersion:
    """Tests for the get_version method."""

    def test_get_version_stable(self, manager):
        """Test get_version returns correct info for stable branch."""
        version_info = manager.get_version()

        assert version_info["branch"] == "stable"
        assert "Build 41" in version_info["branch_display"]
        assert version_info["server_name"] == "testserver"
        assert version_info["base_server_name"] == "testserver"

    def test_get_version_beta(self, manager):
        """Test get_version returns correct info for beta branch."""
        manager._save_version_state("beta")
        version_info = manager.get_version()

        assert version_info["branch"] == "beta"
        assert "Build 42" in version_info["branch_display"]
        assert version_info["server_name"] == "testserver_b42"
        assert version_info["base_server_name"] == "testserver"


class TestGetAvailableVersions:
    """Tests for the get_available_versions method."""

    def test_returns_two_versions(self, manager):
        """Test that exactly two versions are returned."""
        versions = manager.get_available_versions()
        assert len(versions) == 2

    def test_stable_version_info(self, manager):
        """Test stable version information."""
        versions = manager.get_available_versions()
        stable = next(v for v in versions if v["id"] == "stable")

        assert "Build 41" in stable["name"]
        assert "stable" in stable["description"].lower()

    def test_beta_version_info(self, manager):
        """Test beta version information."""
        versions = manager.get_available_versions()
        beta = next(v for v in versions if v["id"] == "beta")

        assert "Build 42" in beta["name"]
        assert "beta" in beta["description"].lower() or "unstable" in beta["description"].lower()

    def test_current_version_is_selected(self, manager):
        """Test that the current version is marked as selected."""
        # On stable
        versions = manager.get_available_versions()
        stable = next(v for v in versions if v["id"] == "stable")
        beta = next(v for v in versions if v["id"] == "beta")
        assert stable["selected"] is True
        assert beta["selected"] is False

        # Switch to beta
        manager._save_version_state("beta")
        versions = manager.get_available_versions()
        stable = next(v for v in versions if v["id"] == "stable")
        beta = next(v for v in versions if v["id"] == "beta")
        assert stable["selected"] is False
        assert beta["selected"] is True


class TestSetVersion:
    """Tests for the set_version method."""

    def test_set_version_requires_server_stopped(self, manager):
        """Test that set_version fails if server is running."""
        from src.game_server_interface import ServerControlError

        manager.server_process = MagicMock()
        manager.server_process.poll.return_value = None
        manager._server_started = True

        with pytest.raises(ServerControlError) as exc_info:
            manager.set_version("beta")

        assert "running" in str(exc_info.value).lower()

    def test_set_version_skips_if_already_on_branch(self, manager):
        """Test that set_version skips update if already on the requested branch."""
        # Already on stable by default
        result = manager.set_version("stable")

        assert "already on" in result.lower()
        assert "no update needed" in result.lower()

    @patch("subprocess.run")
    def test_set_version_runs_steamcmd(self, mock_run, manager):
        """Test that set_version runs SteamCMD."""
        mock_run.return_value = MagicMock(stdout="Success", returncode=0)

        manager.set_version("beta")

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "-beta" in call_args
        assert "unstable" in call_args

    @patch("subprocess.run")
    def test_set_version_updates_state(self, mock_run, manager):
        """Test that set_version updates the state file."""
        mock_run.return_value = MagicMock(stdout="Success", returncode=0)

        manager.set_version("beta")

        assert manager._get_current_branch() == "beta"


class TestBackupPath:
    """Tests for version-specific backup paths."""

    def test_backup_path_stable(self, manager):
        """Test that stable branch uses 'stable' subfolder."""
        backup_path = manager.get_backup_path_for_branch("stable")
        assert backup_path.name == "stable"

    def test_backup_path_beta(self, manager):
        """Test that beta branch uses 'beta' subfolder."""
        backup_path = manager.get_backup_path_for_branch("beta")
        assert backup_path.name == "beta"

    def test_backup_path_current_branch(self, manager):
        """Test that None uses the current branch."""
        # Default is stable
        backup_path = manager.get_backup_path_for_branch()
        assert backup_path.name == "stable"

        # Switch to beta
        manager._save_version_state("beta")
        backup_path = manager.get_backup_path_for_branch()
        assert backup_path.name == "beta"


class TestFirstTimeVersionDetection:
    """Tests for first-time version detection."""

    def test_first_time_beta_no_config(self, manager):
        """Test that first-time switch to beta is detected when no config exists."""
        # No config file exists, so it should be first time
        with patch.object(pathlib.Path, "exists", return_value=False):
            assert manager._is_first_time_version("beta") is True

    def test_not_first_time_if_config_exists(self, manager):
        """Test that it's not first-time if config already exists."""
        with patch.object(pathlib.Path, "exists", return_value=True):
            assert manager._is_first_time_version("beta") is False


class TestSetVersionErrorHandling:
    """Tests for error handling in set_version."""

    @patch("subprocess.run")
    def test_set_version_restores_state_on_steamcmd_failure(self, mock_run, manager):
        """Test that state is restored if SteamCMD fails."""
        from src.game_server_interface import ServerControlError

        # Start on stable
        assert manager._get_current_branch() == "stable"

        # SteamCMD fails
        mock_run.side_effect = subprocess.CalledProcessError(1, "steamcmd")

        with pytest.raises(ServerControlError):
            manager.set_version("beta")

        # State should still be stable (restored on failure)
        assert manager._get_current_branch() == "stable"

    @patch("subprocess.run")
    def test_set_version_timeout_error(self, mock_run, manager):
        """Test that timeout error (code 10) is handled."""
        from src.game_server_interface import ServerControlError

        error = subprocess.CalledProcessError(10, "steamcmd")
        mock_run.side_effect = error

        with pytest.raises(ServerControlError) as exc_info:
            manager.set_version("beta")

        assert "timed out" in str(exc_info.value).lower()

    @patch("subprocess.run")
    def test_set_version_steamcmd_error_134(self, mock_run, manager):
        """Test that SteamCMD error (code 134) is handled."""
        from src.game_server_interface import ServerControlError

        error = subprocess.CalledProcessError(134, "steamcmd")
        mock_run.side_effect = error

        with pytest.raises(ServerControlError) as exc_info:
            manager.set_version("beta")

        assert "error" in str(exc_info.value).lower()


class TestSetVersionMessages:
    """Tests for set_version response messages."""

    @patch("subprocess.run")
    def test_set_version_shows_server_name_change(self, mock_run, manager):
        """Test that set_version shows the server name change."""
        mock_run.return_value = MagicMock(stdout="Success", returncode=0)

        result = manager.set_version("beta")

        assert "testserver" in result
        assert "testserver_b42" in result

    @patch("subprocess.run")
    def test_set_version_shows_first_time_warning(self, mock_run, manager):
        """Test that first-time switch shows config guidance."""
        mock_run.return_value = MagicMock(stdout="Success", returncode=0)

        with patch.object(manager, "_is_first_time_version", return_value=True):
            result = manager.set_version("beta")

        assert "First-time setup" in result or "first-time" in result.lower()
        assert ".ini" in result  # Should mention config file

    @patch("subprocess.run")
    def test_set_version_shows_save_independence_note(self, mock_run, manager):
        """Test that version switch mentions save independence."""
        mock_run.return_value = MagicMock(stdout="Success", returncode=0)

        result = manager.set_version("beta")

        assert "independent" in result.lower() or "separate" in result.lower()


class TestServerNameDynamicChange:
    """Tests to verify server_name changes dynamically with branch."""

    def test_server_name_changes_after_state_update(self, manager):
        """Test that server_name property reflects current branch."""
        # Initially stable
        assert manager.server_name == "testserver"

        # Change to beta
        manager._save_version_state("beta")
        assert manager.server_name == "testserver_b42"

        # Change back to stable
        manager._save_version_state("stable")
        assert manager.server_name == "testserver"

    def test_backup_paths_use_current_server_name(self, manager):
        """Test that backup paths use the correct server name for the branch."""
        # On stable
        paths = manager.get_backup_paths()
        for path in paths.values():
            assert "testserver" in str(path)
            assert "_b42" not in str(path)

        # Switch to beta
        manager._save_version_state("beta")
        paths = manager.get_backup_paths()
        for path in paths.values():
            assert "testserver_b42" in str(path)
