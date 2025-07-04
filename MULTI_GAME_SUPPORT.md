# Multi-Game Discord Bot Updates

## New Features

The Discord bot now supports multiple games through a unified interface:

### Supported Games

- **Palworld** (aliases: `palworld`, `pal`)
- **Project Zomboid** (aliases: `project_zomboid`, `pz`, `zomboid`)

### Command Usage

All commands now accept an optional game type parameter:

```
!start [game_type]     # Start a game server
!stop [game_type]      # Stop a game server
!restart [game_type]   # Restart a game server
!update [game_type]    # Update a game server
!info [game_type]      # Get server information
!ip [game_type]        # Get server IP and port
!games                 # List all supported games
```

### Examples

```
!start pz              # Start Project Zomboid server
!start palworld        # Start Palworld server
!start                 # Start default game server
!stop pz               # Stop Project Zomboid server
!info pal              # Get Palworld server info
!games                 # List all supported games
```

### Configuration

Update your `.env` file with the new configuration options:

```env
# Default game type
DEFAULT_GAME=palworld

# Project Zomboid specific settings
PZ_SERVER_PATH=C:\PZServer
PZ_SERVER_NAME=servertest
PZ_MEMORY_GB=4
```

### Project Zomboid Setup

For Project Zomboid servers:

1. **Download Project Zomboid Dedicated Server** via Steam or SteamCMD (App ID: 380870)
2. **Configure memory settings** via `PZ_MEMORY_GB` environment variable
3. **Set server name** via `PZ_SERVER_NAME` environment variable
4. **Set server path** via `PZ_SERVER_PATH` environment variable

The bot will automatically:

- Create custom batch files with proper memory settings
- Monitor the Java process for server status
- Parse configuration files for server information
- Handle graceful shutdowns

### Architecture

The new system uses:

- **Abstract interfaces** (`GameServerAPI`, `GameServerConductor`) for common functionality
- **Game-specific implementations** for each supported game
- **Server factory pattern** to create appropriate instances
- **Caching** to avoid recreating server instances

### Adding New Games

To add support for a new game:

1. Create a new API class implementing `GameServerAPI`
2. Create a new conductor class extending `GameServerConductor`
3. Update `ServerFactory` to include the new game
4. Add configuration options to `Config` class
5. Update the supported games dictionary

This modular approach makes it easy to extend support to additional games in the future.
