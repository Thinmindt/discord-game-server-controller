import os
import re
from typing import Any, Dict


class PalWorldSettings:
    """Class to manage PalWorldSettings.ini file"""

    def __init__(self, file_path: str):
        """Initialize with the path to the settings file"""
        self.file_path = file_path
        self.section = "/Script/Pal.PalGameWorldSettings"
        self.settings: Dict[str, Any] = {}
        self.load()

    def load(self):
        """Load and parse the settings file"""
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Settings file not found: {self.file_path}")

        with open(self.file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract the OptionSettings value
        pattern = r"OptionSettings=\((.*)\)"
        match = re.search(pattern, content)
        if not match:
            raise ValueError("Could not parse OptionSettings from the file")

        options_str = match.group(1)

        # Parse key-value pairs
        self.settings = self._parse_options(options_str)

    def _parse_options(self, options_str: str) -> Dict[str, Any]:
        """Parse the options string into a dictionary"""
        settings = {}

        # Handle nested parentheses for arrays
        in_array = False
        array_start = 0
        current_pos = 0
        buffer = ""

        while current_pos < len(options_str):
            char = options_str[current_pos]

            if char == "(" and not in_array:
                in_array = True
                array_start = current_pos
            elif char == ")" and in_array:
                in_array = False
                buffer += options_str[array_start : current_pos + 1]
            elif not in_array:
                buffer += char

            current_pos += 1

        # Split by commas, but only top-level commas
        key_values = []
        start = 0
        for i, char in enumerate(buffer):
            if char == "," and not in_array:
                key_values.append(buffer[start:i].strip())
                start = i + 1

        # Add the last key-value pair
        if start < len(buffer):
            key_values.append(buffer[start:].strip())

        # Process each key-value pair
        for kv in key_values:
            if "=" in kv:
                key, value = kv.split("=", 1)
                settings[key] = self._parse_value(value)

        return settings

    def _parse_value(self, value: str) -> Any:
        """Parse a value string into the appropriate Python type"""
        # Handle string values
        if value.startswith('"') and value.endswith('"'):
            return value[1:-1]

        # Handle boolean values
        if value.lower() == "true":
            return True
        if value.lower() == "false":
            return False

        # Handle numeric values
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # Handle arrays
        if value.startswith("(") and value.endswith(")"):
            array_content = value[1:-1]
            if not array_content:
                return []

            # Handle simple comma-separated arrays
            return [self._parse_value(item.strip()) for item in array_content.split(",")]

        # Default case
        return value

    def get(self, key: str) -> Any:
        """Get a setting value by key"""
        return self.settings.get(key)

    def set(self, key: str, value: Any) -> None:
        """Set a setting value"""
        self.settings[key] = value

    def _format_value(self, value: Any) -> str:
        """Format a Python value to string representation for the INI file"""
        if isinstance(value, bool):
            return "True" if value else "False"

        if isinstance(value, str):
            return f'"{value}"'

        if isinstance(value, float):
            return f"{value:.6f}"

        # Numbers and other types
        return str(value)

    def save(self) -> None:
        """Save settings back to the file"""
        # Format all key-value pairs
        formatted_pairs = []
        for key, value in self.settings.items():
            formatted_pairs.append(f"{key}={self._format_value(value)}")

        # Create the OptionSettings string
        options_str = ",".join(formatted_pairs)

        # Read the original file to preserve comments and structure
        with open(self.file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Replace the OptionSettings value
        pattern = r"OptionSettings=\(.*\)"
        replacement = f"OptionSettings=({options_str})"
        updated_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

        # Write back to the file
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.write(updated_content)
