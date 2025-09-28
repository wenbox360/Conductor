# config.py

"""
Configuration settings for the MCP server.
"""

import os
from typing import Dict, Any

# Server configuration
SERVER_NAME = "MHacks 2025 MCP Server"
SERVER_VERSION = "1.0.0"

# Device configuration
DEVICE_TYPE = "Atmega 32u4"  # or "Raspberry Pi 5"

# Environment variables
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Default settings
DEFAULT_SETTINGS: Dict[str, Any] = {
    "max_file_size": 10 * 1024 * 1024,  # 10MB
    "timeout": 30,  # seconds
    "encoding": "utf-8"
}

def get_setting(key: str, default: Any = None) -> Any:
    """Get a configuration setting."""
    return DEFAULT_SETTINGS.get(key, default)