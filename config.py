"""
Configuration module for LAN Audio Streaming
"""

import json
import os
from dataclasses import dataclass, asdict
from typing import Optional

CONFIG_FILE = "config.json"

@dataclass
class AudioConfig:
    """Audio streaming configuration"""
    # Network settings
    peer_ip: str = "192.168.1.100"
    send_port: int = 5001
    receive_port: int = 5002
    
    # Audio settings
    sample_rate: int = 48000  # Optimal for Opus
    channels: int = 2  # Stereo
    chunk_size: int = 960  # 20ms at 48kHz (optimal for Opus)
    
    # Opus settings
    opus_bitrate: int = 64000  # 64 kbps - good quality, low bandwidth
    
    # Device settings
    input_device: Optional[int] = None  # None = default loopback
    output_device: Optional[int] = None  # None = default output
    
    # Volume
    volume: float = 1.0
    
    def save(self, filepath: str = CONFIG_FILE):
        """Save configuration to JSON file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(asdict(self), f, indent=2)
    
    @classmethod
    def load(cls, filepath: str = CONFIG_FILE) -> 'AudioConfig':
        """Load configuration from JSON file"""
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return cls(**data)
            except (json.JSONDecodeError, TypeError):
                pass
        return cls()


def get_default_config() -> AudioConfig:
    """Get default configuration"""
    return AudioConfig.load()
