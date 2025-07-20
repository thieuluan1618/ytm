"""Configuration management for YTM CLI"""

import configparser
from .auth import AuthManager

config = configparser.ConfigParser()
config.read('config.ini')

# Initialize authentication manager and YTMusic instance
auth_manager = AuthManager()
ytmusic = auth_manager.get_ytmusic_instance()

def get_songs_to_display():
    """Get the number of songs to display from config"""
    return int(config.get('general', 'songs_to_display', fallback='5'))

def get_mpv_flags():
    """Get MPV flags from config"""
    if 'mpv' in config and 'flags' in config['mpv']:
        return config['mpv']['flags'].split()
    return []