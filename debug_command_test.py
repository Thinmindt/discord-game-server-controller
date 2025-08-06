#!/usr/bin/env python3
"""Debug script to test server command functionality."""

import sys
import time
from pathlib import Path
from src.project_zomboid_manager import ProjectZomboidServerManager
from src.config import Config


def main():
    """Test server command functionality with a real server."""
    print("🔧 Project Zomboid Command Debug Test")
    print("=" * 50)

    try:
        # Load configuration
        server_path = Config.PZ_SERVER_PATH
        server_name = Config.PZ_SERVER_NAME

        if not server_path or not server_path.exists():
            print(f"❌ Server path not found or not configured: {server_path}")
            print("   Please set PZ_SERVER_PATH in your .env file")
            return 1

        print(f"📂 Server path: {server_path}")
        print(f"🏷️  Server name: {server_name}")

        # Create manager
        manager = ProjectZomboidServerManager(server_path, server_name)

        # Check if server is already running
        if manager.is_on():
            print("✅ Server is already running")
        else:
            print("❌ Server is not running. Please start it first with the CLI tool.")
            print("   Run: python cli_test.py")
            print("   Then use: pz start_server")
            return 1

        # Wait a moment
        print("\n⏳ Waiting 2 seconds before sending test command...")
        time.sleep(2)

        # Test command
        test_commands = ["help", "players", 'servermsg "Test message from debug script"']

        for cmd in test_commands:
            print(f"\n🎯 Testing command: {cmd}")
            print("-" * 30)

            try:
                result = manager.send_server_command(cmd)
                print(f"✅ Command result: {result}")
            except Exception as e:
                print(f"❌ Command failed: {e}")

            print("⏳ Waiting 3 seconds before next command...")
            time.sleep(3)

        print("\n✅ Debug test complete!")
        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
