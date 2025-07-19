"""Configuration management for YTM CLI"""

import configparser
from ytmusicapi import YTMusic

config = configparser.ConfigParser()
config.read('config.ini')

# Initialize YTMusic instance
ytmusic = YTMusic()

def get_songs_to_display():
    """Get the number of songs to display from config"""
    return int(config.get('general', 'songs_to_display', fallback='5'))

def get_mpv_flags():
    """Get MPV flags from config"""
    if 'mpv' in config and 'flags' in config['mpv']:
        return config['mpv']['flags'].split()
    return []