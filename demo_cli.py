#!/usr/bin/env python3
"""
Demo script to show the CLI testing interface in action.
"""

import asyncio
from cli_test import DiscordBotCLI


async def demo():
    """Run a demo of the CLI commands."""
    print("🎬 Running Discord Bot CLI Demo")
    print("=" * 50)

    cli = DiscordBotCLI()

    # Simulate some commands
    demo_commands = [
        ("help", []),
        ("games", []),
        ("info", ["pz"]),
        ("ip", ["palworld"]),
    ]

    for command, args in demo_commands:
        print(f"\n💬 Running command: {command} {' '.join(args)}")
        print("-" * 30)

        if command == "help":
            cli.cmd_help(args)
        elif command == "games":
            await cli.cmd_games(args)
        elif command == "info":
            await cli.cmd_info(args)
        elif command == "ip":
            await cli.cmd_ip(args)

        await asyncio.sleep(1)  # Small delay between commands

    print("\n🎬 Demo completed!")


if __name__ == "__main__":
    asyncio.run(demo())
