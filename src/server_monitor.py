import asyncio
import threading
from typing import Any


class ServerMonitor:
    """Publish output from the server to the Discord channel"""

    def __init__(self, discord_channel_id: str, bot: Any):
        self.stdout_thread = None
        self.stderr_thread = None
        self.discord_channel_id = discord_channel_id
        self.stop_threads = False
        self.bot = bot

    def start_monitoring(self, server_process):
        """Start publishing std_err and std_out to the discord server"""

        print("Starting monitoring threads")
        self.stop_threads = False
        self.stdout_thread = threading.Thread(
            target=self._read_output, args=(server_process.stdout,), daemon=True
        )
        self.stderr_thread = threading.Thread(
            target=self._read_output, args=(server_process.stderr,), daemon=True
        )
        self.stdout_thread.start()
        self.stderr_thread.start()

    def stop_monitoring(self):
        """Stop publishing updates and kill the monitoring threads."""

        print("Stopping monitoring threads")
        self.stop_threads = True
        if self.stdout_thread and self.stdout_thread.is_alive():
            self.stdout_thread.join()

        if self.stderr_thread and self.stderr_thread.is_alive():
            self.stderr_thread.join()

        self.stdout_thread = None
        self.stderr_thread = None

    def _read_output(self, pipe):
        """Continuously read from stdout or stderr until the server stops or the stop signal is triggered."""
        try:
            while not self.stop_threads:
                line = pipe.readline()
                if line:
                    # Publish the line to the Discord channel using bot.loop
                    asyncio.run_coroutine_threadsafe(
                        self._publish_to_discord(line.strip()), self.bot.loop
                    )
                elif self.server_process.poll() is not None:
                    break  # Exit if the process ends
        except Exception as e:
            print(f"Error while reading output: {e}")
        finally:
            pipe.close()  # Ensure the pipe is closed when done

    async def _publish_to_discord(self, message):
        """Publish the server's output to a specific Discord channel."""
        channel = self.bot.get_channel(self.channel_id)
        if channel:
            await channel.send(message)
        else:
            print("Error: no channel found")
