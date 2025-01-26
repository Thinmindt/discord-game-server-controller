# Test updates independently of the discord bot. Uses the config
# stored in .env file.

from src.config import Config
from src.palworld_api import PalworldAPI
from src.server_conductor import ServerConductor


palworld_api = PalworldAPI(Config.API_USERNAME, Config.API_PASSWORD)
server_conductor: ServerConductor = ServerConductor(
    Config.SERVER_PATH, palworld_api, Config.STEAM_CMD_PATH
)


print("Begin updating the server based on the .env config")
server_conductor.update_server()
