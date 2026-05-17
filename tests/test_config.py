"""Tests for ytm_cli.config module"""

import configparser
import os
from unittest.mock import Mock, patch

import pytest

# We need to mock the imports before importing the config module
# since it initializes global objects on import
with patch("ytm_cli.config.configparser.ConfigParser"):
    from ytm_cli.config import get_mpv_flags, get_songs_to_display


class TestGetSongsToDisplay:
    """Tests for get_songs_to_display function"""

    def test_get_songs_to_display_from_config(self):
        """Test getting songs_to_display from config"""
        mock_config = Mock()
        mock_config.get.return_value = "10"

        with patch("ytm_cli.config.config", mock_config):
            result = get_songs_to_display()

            assert result == 10
            mock_config.get.assert_called_once_with("general", "songs_to_display", fallback="5")

    def test_get_songs_to_display_fallback(self):
        """Test fallback value when config is missing"""
        mock_config = Mock()
        mock_config.get.return_value = "5"  # fallback value

        with patch("ytm_cli.config.config", mock_config):
            result = get_songs_to_display()

            assert result == 5

    def test_get_songs_to_display_invalid_value(self):
        """Test handling of invalid config value"""
        mock_config = Mock()
        mock_config.get.return_value = "invalid"

        with patch("ytm_cli.config.config", mock_config):
            with pytest.raises(ValueError):
                get_songs_to_display()

    def test_get_songs_to_display_zero_value(self):
        """Test handling of zero value"""
        mock_config = Mock()
        mock_config.get.return_value = "0"

        with patch("ytm_cli.config.config", mock_config):
            result = get_songs_to_display()

            assert result == 0

    def test_get_songs_to_display_negative_value(self):
        """Test handling of negative value"""
        mock_config = Mock()
        mock_config.get.return_value = "-5"

        with patch("ytm_cli.config.config", mock_config):
            result = get_songs_to_display()

            assert result == -5


class TestGetMpvFlags:
    """Tests for get_mpv_flags function"""

    def test_get_mpv_flags_with_config(self):
        """Test getting MPV flags from config"""
        mock_config = Mock()
        mock_config.__contains__ = Mock(return_value=True)
        mock_config.__getitem__ = Mock(return_value={"flags": "--no-video --volume=50"})

        with patch("ytm_cli.config.config", mock_config):
            result = get_mpv_flags()

            assert result == ["--no-video", "--volume=50"]

    def test_get_mpv_flags_empty_flags(self):
        """Test when flags value is empty"""
        mock_config = Mock()
        mock_config.__contains__ = Mock(return_value=True)
        mock_config.__getitem__ = Mock(return_value={"flags": ""})

        with patch("ytm_cli.config.config", mock_config):
            result = get_mpv_flags()

            assert result == []

    def test_get_mpv_flags_single_flag(self):
        """Test with single flag"""
        mock_config = Mock()
        mock_config.__contains__ = Mock(return_value=True)
        mock_config.__getitem__ = Mock(return_value={"flags": "--no-video"})

        with patch("ytm_cli.config.config", mock_config):
            result = get_mpv_flags()

            assert result == ["--no-video"]

    def test_get_mpv_flags_multiple_flags(self):
        """Test with multiple flags"""
        mock_config = Mock()
        mock_config.__contains__ = Mock(return_value=True)
        mock_config.__getitem__ = Mock(return_value={"flags": "--no-video --volume=75 --loop"})

        with patch("ytm_cli.config.config", mock_config):
            result = get_mpv_flags()

            assert result == ["--no-video", "--volume=75", "--loop"]


class TestConfigModule:
    """Tests for config module initialization and behavior"""

    def test_config_reads_file(self):
        """Test that config reads from ~/.config/ytm-cli/config.ini"""
        with (
            patch("ytm_cli.config.configparser.ConfigParser") as mock_parser_class,
        ):
            mock_parser = Mock()
            mock_parser_class.return_value = mock_parser

            # Re-import to trigger initialization
            import importlib

            import ytm_cli.config

            importlib.reload(ytm_cli.config)

            # Config now lives under ~/.config/ytm-cli/
            mock_parser.read.assert_called_once()
            called_path = mock_parser.read.call_args[0][0]
            assert called_path.endswith(os.path.join(".config", "ytm-cli", "config.ini"))


class TestConfigIntegration:
    """Integration tests for config module"""

    def test_real_config_parsing(self, temp_dir):
        """Test parsing a real config file"""
        config_content = """[general]
songs_to_display = 15
show_thumbnails = false

[mpv]
flags = --no-video --volume=80

[playlists]
directory = my_playlists
"""
        config_path = os.path.join(temp_dir, "config.ini")
        with open(config_path, "w") as f:
            f.write(config_content)

        # Create a real ConfigParser and test it
        config = configparser.ConfigParser()
        config.read(config_path)

        # Test the actual parsing logic
        songs_to_display = int(config.get("general", "songs_to_display", fallback="5"))
        assert songs_to_display == 15

        if "mpv" in config and "flags" in config["mpv"]:
            mpv_flags = config["mpv"]["flags"].split()
        else:
            mpv_flags = []

        assert mpv_flags == ["--no-video", "--volume=80"]
