"""Configuration management for YTM CLI"""

import configparser
from pathlib import Path


def get_config_dir() -> Path:
    """Get the config directory path (~/.config/ytm-cli/)"""
    config_dir = Path.home() / ".config" / "ytm-cli"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_path() -> str:
    """Get the full path to config.ini"""
    return str(get_config_dir() / "config.ini")


config = configparser.ConfigParser()
config.read(get_config_path())

_ytmusic = None


def get_ytmusic():
    """Get cached YTMusic instance (unauthenticated)"""
    global _ytmusic
    if _ytmusic is None:
        from ytmusicapi import YTMusic

        _ytmusic = YTMusic()
    return _ytmusic


def get_songs_to_display():
    """Get the number of songs to display from config"""
    return int(config.get("general", "songs_to_display", fallback="5"))


def get_mpv_flags():
    """Get MPV flags from config"""
    if "mpv" in config and "flags" in config["mpv"]:
        return config["mpv"]["flags"].split()
    return []


def get_config_value(section, key, fallback=None):
    """Get a value from the config"""
    return config.get(section, key, fallback=fallback)
