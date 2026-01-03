# Discord Game Server Controller

A Discord bot for managing game servers remotely. Control your Palworld and Project Zomboid dedicated servers directly from Discord with simple commands.

## Features

- 🎮 **Multi-Game Support** - Manage Palworld and Project Zomboid servers
- 🚀 **Server Control** - Start, stop, restart, and update servers
- 📊 **Server Info** - View server status, player counts, and connection info
- 💾 **Backups** - Create and manage server backups with automatic cleanup
- 🔧 **Admin Commands** - Send ad-hoc admin commands to running servers
- 🖥️ **CLI Testing** - Test commands locally without Discord

## Supported Games

| Game            | Aliases                            | Features                                      |
| --------------- | ---------------------------------- | --------------------------------------------- |
| Palworld        | `palworld`, `pal`                  | REST API monitoring, server control           |
| Project Zomboid | `project_zomboid`, `pz`, `zomboid` | Log-based monitoring, admin commands, backups |

## Discord Commands

| Command                 | Description             | Example                     |
| ----------------------- | ----------------------- | --------------------------- |
| `!start [game]`         | Start the game server   | `!start pz`                 |
| `!stop [game]`          | Stop the game server    | `!stop palworld`            |
| `!restart [game]`       | Restart the game server | `!restart`                  |
| `!update [game]`        | Update via SteamCMD     | `!update pz`                |
| `!info [game]`          | Show server information | `!info`                     |
| `!ip [game]`            | Show server IP address  | `!ip pz`                    |
| `!backup [game]`        | Create a server backup  | `!backup pz`                |
| `!cmd <game> <command>` | Send admin command      | `!cmd pz servermsg "Hello"` |
| `!games`                | List supported games    | `!games`                    |

## Installation

### Prerequisites

- Python 3.14+
- [SteamCMD](https://developer.valvesoftware.com/wiki/SteamCMD) (for server updates)
- Discord Bot Token ([create one here](https://discord.com/developers/applications))

### Setup

1. **Clone the repository:**

   ```bash
   git clone https://github.com/Thinmindt/discord-game-server-controller.git
   cd discord-game-server-controller
   ```

2. **Create and activate virtual environment:**

   ```bash
   python -m venv .venv

   # Windows (PowerShell)
   .venv\Scripts\activate

   # Linux/Mac
   source .venv/bin/activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r dependencies/requirements.txt
   ```

4. **Configure environment:**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` with your settings:

   ```dotenv
   # Discord Bot Configuration
   DISCORD_TOKEN=your_discord_bot_token_here
   DISCORD_CHANNEL_ID=your_channel_id_here
   DEFAULT_GAME=palworld

   # Common Configuration
   STEAM_CMD_PATH=C:\steamcmd\steamcmd.exe

   # Palworld Configuration
   PALWORLD_SERVER_PATH=C:\PalServer\PalServer.exe
   PALWORLD_SERVER_REST_API_USERNAME=admin
   PALWORLD_SERVER_REST_API_PASSWORD=your_admin_password

   # Project Zomboid Configuration
   PZ_SERVER_PATH=C:\PZServer
   PZ_SERVER_NAME=servertest
   PZ_MEMORY_GB=4
   PZ_BACKUP_PATH=D:\ZomboidServerBackup
   ```

5. **Run the bot:**
   ```bash
   python main.py
   ```

## CLI Testing

Test commands locally without connecting to Discord:

```bash
python cli_test.py
```

```
💬 You: games
🤖 Bot: Supported games:
**Palworld**: `palworld`, `pal`
**Project Zomboid**: `project_zomboid`, `pz`, `zomboid`

💬 You: start pz
🤖 Bot: Starting Project Zomboid server...
```

See [docs/CLI_TESTING.md](docs/CLI_TESTING.md) for more details.

## Development

### Code Quality

```bash
# Format code
ruff format .

# Lint (with auto-fix)
ruff check . --fix

# Type check
mypy .

# Run tests
pytest
```

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for the full development guide.

## License

See [LICENSE](LICENSE) for details.
