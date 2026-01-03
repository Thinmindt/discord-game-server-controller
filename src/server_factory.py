from src.config import Config
from src.game_server_interface import GameServerManager
from src.palworld_manager import PalworldServerManager
from src.project_zomboid_manager import ProjectZomboidServerManager


class ServerFactory:
    """Factory class to create game-specific server manager instances."""

    @staticmethod
    def create_server_manager(game_type: str) -> GameServerManager:
        """Create a unified server manager instance for the specified game type.

        Args:
            game_type: Either 'palworld', 'pz', or 'project_zomboid'

        Returns:
            GameServerManager instance
        """
        game_type = game_type.lower()

        if game_type in ["palworld", "pal"]:
            if not Config.PALWORLD_API_USERNAME or not Config.PALWORLD_API_PASSWORD:
                raise ValueError("Palworld requires API_USERNAME and API_PASSWORD to be set")

            return PalworldServerManager(
                server_path=Config.PALWORLD_SERVER_PATH,
                steam_cmd_path=Config.STEAM_CMD_PATH,
                username=Config.PALWORLD_API_USERNAME,
                password=Config.PALWORLD_API_PASSWORD,
            )

        elif game_type in ["project_zomboid", "pz", "zomboid"]:
            # For PZ, we might need different config values
            server_name = getattr(Config, "PZ_SERVER_NAME", "servertest")
            memory_gb = getattr(Config, "PZ_MEMORY_GB", 10)
            server_path = (
                Config.PZ_SERVER_PATH
                if hasattr(Config, "PZ_SERVER_PATH")
                else Config.PALWORLD_SERVER_PATH
            )

            return ProjectZomboidServerManager(
                server_path=server_path,
                steam_cmd_path=Config.STEAM_CMD_PATH,
                server_name=server_name,
                memory_gb=memory_gb,
            )

        else:
            raise ValueError(f"Unsupported game type: {game_type}")

    @staticmethod
    def get_supported_games() -> dict[str, list[str]]:
        """Get a dictionary of supported games and their aliases."""
        return {
            "palworld": ["palworld", "pal"],
            "project_zomboid": ["project_zomboid", "pz", "zomboid"],
        }

    @staticmethod
    def is_supported_game(game_type: str) -> bool:
        """Check if the game type is supported."""
        game_type_lower = game_type.lower()
        supported_games = ServerFactory.get_supported_games()

        for game_name, aliases in supported_games.items():
            if game_type_lower in aliases:
                return True
        return False
