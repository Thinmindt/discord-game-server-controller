#!/usr/bin/env python3
"""Test script to simulate the buffer overflow issue."""

import threading
import time
from src.project_zomboid_manager import ProjectZomboidServerManager
from pathlib import Path


def test_buffer_overflow_scenario():
    """Test output capture when buffer is at maximum capacity."""
    print("🧪 Testing buffer overflow scenario")

    # Create a manager instance (we won't actually start a server)
    manager = ProjectZomboidServerManager(
        server_path=Path("test_path"), steam_cmd_path=Path("test_steam"), server_name="test_server"
    )

    # Simulate a full buffer (100 lines)
    with manager._log_lines_lock:
        # Fill buffer to capacity
        for i in range(100):
            manager._log_lines.append(f"LOG: Existing line {i}")

        print(f"Buffer filled to: {len(manager._log_lines)} lines")
        print(f"Last few lines: {manager._log_lines[-3:]}")

    # Now test the marker logic
    print("\n🎯 Testing marker-based new line detection...")

    # Simulate taking a snapshot (like before sending command)
    with manager._log_lines_lock:
        if manager._log_lines:
            marker_lines = manager._log_lines[-2:]  # Use last 2 lines as marker
        else:
            marker_lines = []
        buffer_size_before = len(manager._log_lines)

    print(f"Marker lines: {marker_lines}")
    print(f"Buffer size before: {buffer_size_before}")

    # Simulate new lines arriving (like server output)
    with manager._log_lines_lock:
        # Add new lines - this will push old lines out due to 100-line limit
        manager._log_lines.append("LOG: NEW command entered via server console")
        manager._log_lines.append("LOG: NEW User grug no longer has access level")

        # Keep only last 100 lines (simulate the buffer management)
        if len(manager._log_lines) > 100:
            manager._log_lines = manager._log_lines[-100:]

    print(f"Buffer size after: {len(manager._log_lines)}")
    print(f"Last few lines: {manager._log_lines[-3:]}")

    # Test the marker detection logic
    with manager._log_lines_lock:
        current_buffer = manager._log_lines.copy()

    # Find new lines after the marker
    new_lines_found = []
    if marker_lines:
        marker_found = False
        for i, line in enumerate(current_buffer):
            if not marker_found:
                if line == marker_lines[-1]:
                    marker_found = True
                    new_lines_found = current_buffer[i + 1 :]
                    break

    print(f"\n✅ Results:")
    print(f"New lines found: {len(new_lines_found)}")
    print(f"New lines: {new_lines_found}")

    # Test if our new lines were detected correctly
    expected_new_lines = [
        "LOG: NEW command entered via server console",
        "LOG: NEW User grug no longer has access level",
    ]

    success = new_lines_found == expected_new_lines
    print(f"Test result: {'✅ PASS' if success else '❌ FAIL'}")

    return success


if __name__ == "__main__":
    test_buffer_overflow_scenario()
