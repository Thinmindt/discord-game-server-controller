from typing import Dict, Tuple

from src.config import Config
from src.game_server_interface import GameServerAPI, GameServerConductor
from src.palworld_api import PalworldAPI
from src.project_zomboid_api import ProjectZomboidAPI
from src.palworld_conductor import PalworldServerConductor
from src.project_zomboid_conductor import ProjectZomboidServerConductor


class ServerFactory:
    """Factory class to create game-specific server instances."""

    @staticmethod
    def create_server_instances(
        game_type: str,
    ) -> Tuple[GameServerAPI, GameServerConductor]:
        """Create API and Conductor instances for the specified game type.

        Args:
            game_type: Either 'palworld', 'pz', or 'project_zomboid'

        Returns:
            Tuple of (GameServerAPI, GameServerConductor)
        """
        game_type = game_type.lower()

        if game_type in ["palworld", "pal"]:
            if not Config.PALWORLD_API_USERNAME or not Config.PALWORLD_API_PASSWORD:
                raise ValueError("Palworld requires API_USERNAME and API_PASSWORD to be set")
            api: GameServerAPI = PalworldAPI(
                Config.PALWORLD_API_USERNAME, Config.PALWORLD_API_PASSWORD
            )
            conductor: GameServerConductor = PalworldServerConductor(
                Config.PALWORLD_SERVER_PATH, api, Config.STEAM_CMD_PATH
            )
            return api, conductor

        elif game_type in ["project_zomboid", "pz", "zomboid"]:
            # For PZ, we might need different config values
            server_name = getattr(Config, "PZ_SERVER_NAME", "servertest")
            memory_gb = getattr(Config, "PZ_MEMORY_GB", 4)

            api = ProjectZomboidAPI(server_name)
            conductor = ProjectZomboidServerConductor(
                (
                    Config.PZ_SERVER_PATH
                    if hasattr(Config, "PZ_SERVER_PATH")
                    else Config.PALWORLD_SERVER_PATH
                ),
                api,
                Config.STEAM_CMD_PATH,
                server_name=server_name,
                memory_gb=memory_gb,
            )
            return api, conductor

        else:
            raise ValueError(f"Unsupported game type: {game_type}")

    @staticmethod
    def get_supported_games() -> Dict[str, str]:
        """Get a dictionary of supported game aliases and their full names."""
        return {
            "palworld": "Palworld",
            "pal": "Palworld",
            "project_zomboid": "Project Zomboid",
            "pz": "Project Zomboid",
            "zomboid": "Project Zomboid",
        }

    @staticmethod
    def is_supported_game(game_type: str) -> bool:
        """Check if the game type is supported."""
        return game_type.lower() in ServerFactory.get_supported_games()
