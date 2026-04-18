"""Tests for the PZ setmods functionality."""

import pathlib
import tempfile

import pytest

from src.game_server_interface import ServerControlError
from src.project_zomboid_manager import ProjectZomboidServerManager


@pytest.fixture
def manager(tmp_path: pathlib.Path) -> ProjectZomboidServerManager:
    return ProjectZomboidServerManager(
        server_path=tmp_path / "server",
        steam_cmd_path=tmp_path / "steamcmd",
        server_name="TestServer",
    )


def make_mod_info(folder: pathlib.Path, mod_id: str, requires: list[str] | None = None) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    resolved = requires or []
    require_line = f"require={','.join(resolved)}\n" if resolved else ""
    (folder / "mod.info").write_text(f"name=Test Mod\nid={mod_id}\n{require_line}")


class TestTopologicalSort:
    def test_no_dependencies(self, manager: ProjectZomboidServerManager) -> None:
        result = manager._topological_sort(["c", "a", "b"], {})
        assert set(result) == {"a", "b", "c"}
        assert len(result) == 3

    def test_single_chain(self, manager: ProjectZomboidServerManager) -> None:
        deps = {"c": ["b"], "b": ["a"], "a": []}
        result = manager._topological_sort(["a", "b", "c"], deps)
        assert result.index("a") < result.index("b")
        assert result.index("b") < result.index("c")

    def test_shared_dependency(self, manager: ProjectZomboidServerManager) -> None:
        deps = {"b": ["lib"], "c": ["lib"], "lib": []}
        result = manager._topological_sort(["b", "c", "lib"], deps)
        assert result.index("lib") < result.index("b")
        assert result.index("lib") < result.index("c")

    def test_ignores_deps_outside_set(self, manager: ProjectZomboidServerManager) -> None:
        deps = {"a": ["external_lib"]}
        result = manager._topological_sort(["a"], deps)
        assert result == ["a"]

    def test_circular_deps_dont_crash(self, manager: ProjectZomboidServerManager) -> None:
        deps = {"a": ["b"], "b": ["a"]}
        result = manager._topological_sort(["a", "b"], deps)
        assert set(result) == {"a", "b"}


class TestReadWorkshopMods:
    def test_reads_single_mod(self, manager: ProjectZomboidServerManager) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workshop_content = pathlib.Path(tmp)
            make_mod_info(workshop_content / "111" / "mods" / "MyMod", "MyMod")

            result = manager._read_workshop_mods(workshop_content, "111")
            assert result == [("MyMod", [])]

    def test_reads_requires(self, manager: ProjectZomboidServerManager) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workshop_content = pathlib.Path(tmp)
            make_mod_info(workshop_content / "222" / "mods" / "MyMod", "MyMod", ["libA", "libB"])

            result = manager._read_workshop_mods(workshop_content, "222")
            assert result == [("MyMod", ["libA", "libB"])]

    def test_reads_multiple_mods_from_one_item(self, manager: ProjectZomboidServerManager) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workshop_content = pathlib.Path(tmp)
            make_mod_info(workshop_content / "333" / "mods" / "ModA", "ModA")
            make_mod_info(workshop_content / "333" / "mods" / "ModB", "ModB")

            result = manager._read_workshop_mods(workshop_content, "333")
            mod_ids = [r[0] for r in result]
            assert "ModA" in mod_ids
            assert "ModB" in mod_ids

    def test_raises_for_missing_item(self, manager: ProjectZomboidServerManager) -> None:
        with tempfile.TemporaryDirectory() as tmp, pytest.raises(
            ServerControlError, match="not found locally"
        ):
            manager._read_workshop_mods(pathlib.Path(tmp), "nonexistent")

    def test_strips_leading_backslash_from_requires(
        self, manager: ProjectZomboidServerManager
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workshop_content = pathlib.Path(tmp)
            folder = workshop_content / "444" / "mods" / "MyMod"
            folder.mkdir(parents=True)
            (folder / "mod.info").write_text("id=MyMod\nrequire=\\libA,\\libB\n")

            result = manager._read_workshop_mods(workshop_content, "444")
            assert result == [("MyMod", ["libA", "libB"])]


class TestUpdateIniMods:
    def test_updates_both_lines(self, manager: ProjectZomboidServerManager) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ini_path = pathlib.Path(tmp) / "Server" / "TestServer.ini"
            ini_path.parent.mkdir(parents=True)
            ini_path.write_text(
                "PVP=true\nMods=oldMod1;oldMod2\nMap=Muldraugh, KY\nWorkshopItems=111;222\n"
            )

            import unittest.mock as mock

            with mock.patch.object(
                manager,
                "get_backup_paths",
                return_value={"server_ini": ini_path},
            ):
                manager._update_ini_mods(["newMod1", "newMod2"], ["333", "444"])

            content = ini_path.read_text()
            assert "Mods=newMod1;newMod2\n" in content
            assert "WorkshopItems=333;444\n" in content
            assert "PVP=true" in content
            assert "Map=Muldraugh, KY" in content

    def test_raises_if_ini_missing(self, manager: ProjectZomboidServerManager) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing_path = pathlib.Path(tmp) / "nonexistent.ini"
            import unittest.mock as mock

            with mock.patch.object(
                manager,
                "get_backup_paths",
                return_value={"server_ini": missing_path},
            ), pytest.raises(ServerControlError, match="not found"):
                manager._update_ini_mods(["mod"], ["111"])


class TestSetMods:
    def test_full_flow(self, manager: ProjectZomboidServerManager) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workshop_content = pathlib.Path(tmp) / "workshop"
            make_mod_info(workshop_content / "111" / "mods" / "libA", "libA")
            make_mod_info(workshop_content / "222" / "mods" / "modB", "modB", ["libA"])

            ini_path = pathlib.Path(tmp) / "Server" / "TestServer.ini"
            ini_path.parent.mkdir(parents=True)
            ini_path.write_text("Mods=\nWorkshopItems=\n")

            import unittest.mock as mock

            with (
                mock.patch.object(manager, "_find_pz_workshop_path", return_value=workshop_content),
                mock.patch.object(
                    manager,
                    "get_backup_paths",
                    return_value={"server_ini": ini_path},
                ),
            ):
                result = manager.set_mods(["111", "222"])

            assert "2 mods" in result
            content = ini_path.read_text()
            lines = {line.split("=")[0]: line for line in content.splitlines() if "=" in line}
            mods = lines["Mods"].split("=", 1)[1].split(";")
            assert mods.index("libA") < mods.index("modB")

    def test_reports_missing_workshop_items(self, manager: ProjectZomboidServerManager) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workshop_content = pathlib.Path(tmp) / "workshop"
            make_mod_info(workshop_content / "111" / "mods" / "libA", "libA")

            ini_path = pathlib.Path(tmp) / "Server" / "TestServer.ini"
            ini_path.parent.mkdir(parents=True)
            ini_path.write_text("Mods=\nWorkshopItems=\n")

            import unittest.mock as mock

            with (
                mock.patch.object(manager, "_find_pz_workshop_path", return_value=workshop_content),
                mock.patch.object(
                    manager,
                    "get_backup_paths",
                    return_value={"server_ini": ini_path},
                ),
            ):
                result = manager.set_mods(["111", "999"])

            assert "999" in result
            assert "subscribe" in result.lower()
