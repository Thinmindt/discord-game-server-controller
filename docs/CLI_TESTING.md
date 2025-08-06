# Discord Bot CLI Testing Interface

This command line interface allows you to test all Discord bot commands locally without needing to connect to Discord or bother people in your Discord channel.

## Features

- 🚀 **Complete Command Coverage**: Test all Discord bot commands (`start`, `stop`, `restart`, `update`, `info`, `ip`, `games`, `cmd`)
- 🎮 **Multi-Game Support**: Test commands for both Palworld and Project Zomboid
- 🤖 **Mock Discord Context**: Simulates Discord bot responses
- 💻 **Interactive CLI**: Real-time command testing with immediate feedback
- 🔄 **Async Support**: Proper async/await handling like the real Discord bot
- 📨 **Server Commands**: Send ad-hoc admin commands to running game servers

## Quick Start

### Windows

```cmd
run_cli_test.bat
```

### Linux/Mac

```bash
chmod +x run_cli_test.sh
./run_cli_test.sh
```

### Direct Python

```bash
python cli_test.py
```

## Usage Examples

```
💬 You: help
🤖 Bot: [Shows complete help information]

💬 You: games
🤖 Bot: Supported games:
**Palworld**: `palworld`, `pal`
**Project Zomboid**: `project_zomboid`, `pz`, `zomboid`
Default game: `palworld`

💬 You: start pz
🤖 Bot: Starting Project Zomboid server...
🤖 Bot: Project Zomboid server started!

💬 You: info palworld
🤖 Bot: Palworld Server Info:
Server Name: MyServer
Version: 1.0.0
...

💬 You: ip pz
🤖 Bot: The Project Zomboid server host IP address is: 192.168.1.100:16261

💬 You: cmd pz teleport player1 player2
🤖 Bot: Sending command to Project Zomboid server: teleport player1 player2
🤖 Bot: Server response:
```

Player player1 teleported to player2

```

💬 You: quit
👋 Goodbye!
```

## Available Commands

### Game Server Commands

- `start [game_type]` - Start a game server
- `stop [game_type]` - Stop a game server
- `restart [game_type]` - Restart a game server
- `update [game_type]` - Update a game server (must be stopped first)
- `info [game_type]` - Get server information
- `ip [game_type]` - Get server IP and port
- `cmd <game_type> <command> [args...]` - Send admin command to running server
- `games` - List all supported games

### CLI Commands

- `help` - Show help information
- `quit` / `exit` - Exit the CLI

### Game Types

- `palworld` or `pal` - Palworld server
- `project_zomboid`, `pz`, or `zomboid` - Project Zomboid server
- If no game type is specified, the default game from config is used

## Demo Mode

Run a non-interactive demo to see the CLI in action:

```bash
python demo_cli.py
```

## Benefits for Development

1. **No Discord Setup Required**: Test bot logic without Discord credentials
2. **Fast Iteration**: Immediate feedback without Discord API delays
3. **Offline Testing**: Works without internet connection
4. **Debug Friendly**: See exact bot responses and error messages
5. **Safe Testing**: No risk of spamming Discord channels
6. **Full Functionality**: Tests the same code paths as the real Discord bot

## Implementation Details

The CLI:

- Uses the exact same command functions as the Discord bot
- Implements a `MockContext` class that simulates Discord's `ctx.send()`
- Handles all the same error cases and edge conditions
- Supports both synchronous and asynchronous operations
- Maintains server state between commands (like the real bot)

## Configuration

The CLI uses the same configuration as the Discord bot:

- Environment variables from `.env` file
- Same server paths and credentials
- Same default game settings

Make sure your `.env` file is properly configured before running the CLI.

## Troubleshooting

### "Command not found" errors

Make sure you're in the correct directory and have activated your Python environment.

### Configuration errors

Ensure your `.env` file has the required configuration for the game you're testing:

- For Palworld: `SERVER_PATH`, `API_USERNAME`, `API_PASSWORD`
- For Project Zomboid: `PZ_SERVER_PATH`, `PZ_SERVER_NAME`

### Permission errors

On Linux/Mac, you may need to make the shell script executable:

```bash
chmod +x run_cli_test.sh
```

## Advanced Usage

### Custom Commands

You can extend the CLI by adding new command methods following the pattern:

```python
async def cmd_your_command(self, args: List[str]) -> None:
    """Your custom command."""
    # Implementation here
```

### Scripted Testing

Create your own demo scripts to test specific scenarios:

```python
import asyncio
from cli_test import DiscordBotCLI

async def my_test():
    cli = DiscordBotCLI()
    await cli.cmd_start(["pz"])
    await cli.cmd_info(["pz"])
    await cli.cmd_stop(["pz"])

asyncio.run(my_test())
```
