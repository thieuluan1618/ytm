"""Integration tests for YTM CLI components"""

import json
import os
import tempfile
from unittest.mock import Mock, patch

import pytest

from ytm_cli.auth import AuthManager
from ytm_cli.dislikes import DislikeManager
from ytm_cli.playlists import PlaylistManager


class TestPlaylistDislikeIntegration:
    """Integration tests between playlist and dislike managers"""

    def test_playlist_with_disliked_songs(self, temp_dir, sample_songs):
        """Test playlist functionality with disliked songs"""
        # Setup managers
        playlist_manager = PlaylistManager(temp_dir)
        dislikes_file = os.path.join(temp_dir, "dislikes.json")
        dislike_manager = DislikeManager(dislikes_file)
        
        # Create playlist and add songs
        with patch('builtins.print'):
            playlist_manager.create_playlist("Test Playlist")
            for song in sample_songs:
                playlist_manager.add_song_to_playlist("Test Playlist", song)
        
        # Dislike one song
        with patch('builtins.print'):
            dislike_manager.dislike_song(sample_songs[1])  # Dislike "song2"
        
        # Get playlist and filter disliked songs
        playlist_data = playlist_manager.get_playlist("Test Playlist")
        playlist_songs = playlist_data["songs"]
        
        # Convert playlist songs to the format expected by dislike manager
        converted_songs = []
        for song in playlist_songs:
            converted_song = {
                "videoId": song["videoId"],
                "title": song["title"],
                "artists": [{"name": song["artist"]}]
            }
            converted_songs.append(converted_song)
        
        with patch('builtins.print'):
            filtered_songs = dislike_manager.filter_disliked_songs(converted_songs)
        
        # Should have 2 songs left (song1 and song3)
        assert len(filtered_songs) == 2
        video_ids = [song["videoId"] for song in filtered_songs]
        assert "song1" in video_ids
        assert "song3" in video_ids
        assert "song2" not in video_ids

    def test_playlist_creation_with_auth_enabled(self, temp_dir):
        """Test playlist creation when authentication is enabled"""
        # Setup auth manager with enabled auth
        config_file = os.path.join(temp_dir, "config.ini")
        auth_manager = AuthManager(config_file=config_file)
        
        with patch('builtins.print'):
            auth_manager.enable_auth("oauth")
        
        # Setup playlist manager
        playlist_manager = PlaylistManager(temp_dir)
        
        # Create playlist - should work regardless of auth status
        with patch('builtins.print'):
            result = playlist_manager.create_playlist("Auth Test Playlist")
        
        assert result is True
        assert auth_manager.is_auth_enabled() is True
        
        # Verify playlist exists
        playlists = playlist_manager.list_playlists()
        assert len(playlists) == 1
        assert playlists[0]["name"] == "Auth Test Playlist"

    def test_dislike_persistence_across_playlist_operations(self, temp_dir, sample_songs):
        """Test that dislikes persist across playlist operations"""
        dislikes_file = os.path.join(temp_dir, "dislikes.json")
        dislike_manager = DislikeManager(dislikes_file)
        playlist_manager = PlaylistManager(temp_dir)
        
        # Dislike a song first
        with patch('builtins.print'):
            dislike_manager.dislike_song(sample_songs[0])
        
        # Create playlist and add songs
        with patch('builtins.print'):
            playlist_manager.create_playlist("Test Playlist")
            for song in sample_songs:
                playlist_manager.add_song_to_playlist("Test Playlist", song)
        
        # Create new dislike manager instance to test persistence
        dislike_manager2 = DislikeManager(dislikes_file)
        
        # Should still have the disliked song
        assert dislike_manager2.is_disliked("song1")
        assert dislike_manager2.get_dislike_count() == 1


class TestAuthConfigIntegration:
    """Integration tests between auth and config management"""

    def test_auth_config_file_management(self, temp_dir):
        """Test auth configuration file management"""
        config_file = os.path.join(temp_dir, "config.ini")
        oauth_file = os.path.join(temp_dir, "oauth.json")
        
        auth_manager = AuthManager(
            oauth_file=oauth_file,
            config_file=config_file
        )
        
        # Initially no auth
        assert auth_manager.is_auth_enabled() is False
        
        # Enable OAuth
        with patch('builtins.print'):
            auth_manager.enable_auth("oauth")
        
        assert auth_manager.is_auth_enabled() is True
        assert auth_manager.get_auth_method() == "oauth"
        
        # Create new instance to test persistence
        auth_manager2 = AuthManager(config_file=config_file)
        assert auth_manager2.is_auth_enabled() is True
        assert auth_manager2.get_auth_method() == "oauth"
        
        # Disable auth
        with patch('builtins.print'):
            auth_manager2.disable_auth()
        
        # Create third instance to verify disable persisted
        auth_manager3 = AuthManager(config_file=config_file)
        assert auth_manager3.is_auth_enabled() is False

    def test_auth_with_ytmusic_instance_creation(self, temp_dir):
        """Test YTMusic instance creation with different auth states"""
        config_file = os.path.join(temp_dir, "config.ini")
        oauth_file = os.path.join(temp_dir, "oauth.json")
        
        auth_manager = AuthManager(
            oauth_file=oauth_file,
            config_file=config_file
        )
        
        # Test unauthenticated instance
        with patch('ytmusicapi.YTMusic') as mock_ytmusic, \
             patch('builtins.print'):
            
            mock_instance = Mock()
            mock_ytmusic.return_value = mock_instance
            
            instance = auth_manager.get_ytmusic_instance()
            
            assert instance == mock_instance
            mock_ytmusic.assert_called_once_with()
        
        # Enable auth and create OAuth file
        oauth_data = {"access_token": "test_token"}
        with open(oauth_file, 'w') as f:
            json.dump(oauth_data, f)
        
        with patch('builtins.print'):
            auth_manager.enable_auth("oauth")
        
        # Test authenticated instance
        with patch('ytmusicapi.YTMusic') as mock_ytmusic, \
             patch('builtins.print'):
            
            mock_instance = Mock()
            mock_ytmusic.return_value = mock_instance
            
            instance = auth_manager.get_ytmusic_instance()
            
            assert instance == mock_instance
            mock_ytmusic.assert_called_once_with(oauth_file)


class TestFullWorkflowIntegration:
    """Integration tests for complete workflows"""

    def test_complete_playlist_workflow(self, temp_dir, sample_songs):
        """Test complete playlist workflow from creation to playback"""
        playlist_manager = PlaylistManager(temp_dir)
        dislikes_file = os.path.join(temp_dir, "dislikes.json")
        dislike_manager = DislikeManager(dislikes_file)
        
        with patch('builtins.print'):
            # Create playlist
            result = playlist_manager.create_playlist("My Workflow Playlist", "Test playlist")
            assert result is True
            
            # Add songs to playlist
            for song in sample_songs:
                result = playlist_manager.add_song_to_playlist("My Workflow Playlist", song)
                assert result is True
            
            # Verify playlist contents
            playlist_data = playlist_manager.get_playlist("My Workflow Playlist")
            assert playlist_data is not None
            assert len(playlist_data["songs"]) == 3
            
            # Dislike one song
            dislike_manager.dislike_song(sample_songs[1])
            
            # Get playlist songs and filter dislikes
            playlist_songs = playlist_data["songs"]
            converted_songs = []
            for song in playlist_songs:
                converted_song = {
                    "videoId": song["videoId"],
                    "title": song["title"],
                    "artists": [{"name": song["artist"]}]
                }
                converted_songs.append(converted_song)
            
            filtered_songs = dislike_manager.filter_disliked_songs(converted_songs)
            assert len(filtered_songs) == 2
            
            # Remove a song from playlist
            result = playlist_manager.remove_song_from_playlist("My Workflow Playlist", "song3")
            assert result is True
            
            # Verify final state
            final_playlist = playlist_manager.get_playlist("My Workflow Playlist")
            assert len(final_playlist["songs"]) == 2
            
            # Delete playlist
            result = playlist_manager.delete_playlist("My Workflow Playlist")
            assert result is True
            
            # Verify deletion
            deleted_playlist = playlist_manager.get_playlist("My Workflow Playlist")
            assert deleted_playlist is None

    def test_auth_setup_to_usage_workflow(self, temp_dir):
        """Test complete auth workflow from setup to usage"""
        config_file = os.path.join(temp_dir, "config.ini")
        oauth_file = os.path.join(temp_dir, "oauth.json")
        
        auth_manager = AuthManager(
            oauth_file=oauth_file,
            config_file=config_file
        )
        
        with patch('builtins.print'):
            # Setup OAuth
            mock_oauth_data = {"access_token": "test_token", "refresh_token": "refresh_token"}
            
            with patch('ytmusicapi.setup.setup_oauth', return_value=mock_oauth_data):
                result = auth_manager.setup_oauth_auth("client_id", "client_secret")
                assert result is True
            
            # Verify auth is enabled
            assert auth_manager.is_auth_enabled() is True
            assert auth_manager.get_auth_method() == "oauth"
            
            # Verify OAuth file was created
            assert os.path.exists(oauth_file)
            with open(oauth_file, 'r') as f:
                saved_data = json.load(f)
                assert saved_data == mock_oauth_data
            
            # Test YTMusic instance creation
            with patch('ytmusicapi.YTMusic') as mock_ytmusic:
                mock_instance = Mock()
                mock_ytmusic.return_value = mock_instance
                
                instance = auth_manager.get_ytmusic_instance()
                
                assert instance == mock_instance
                mock_ytmusic.assert_called_once_with(oauth_file)
            
            # Disable auth
            result = auth_manager.disable_auth()
            assert result is True
            assert auth_manager.is_auth_enabled() is False

    def test_error_recovery_workflow(self, temp_dir, sample_songs):
        """Test error recovery in integrated workflows"""
        playlist_manager = PlaylistManager(temp_dir)
        dislikes_file = os.path.join(temp_dir, "dislikes.json")
        dislike_manager = DislikeManager(dislikes_file)
        
        with patch('builtins.print'):
            # Create playlist successfully
            playlist_manager.create_playlist("Error Test Playlist")
            
            # Try to add song with missing data
            incomplete_song = {"title": "Incomplete Song"}  # Missing videoId
            result = playlist_manager.add_song_to_playlist("Error Test Playlist", incomplete_song)
            # Should handle gracefully (behavior depends on implementation)
            
            # Add valid songs
            for song in sample_songs:
                playlist_manager.add_song_to_playlist("Error Test Playlist", song)
            
            # Try to dislike song with missing videoId
            result = dislike_manager.dislike_song(incomplete_song)
            assert result is False  # Should fail gracefully
            
            # Dislike valid song
            result = dislike_manager.dislike_song(sample_songs[0])
            assert result is True
            
            # Verify system is still functional
            playlist_data = playlist_manager.get_playlist("Error Test Playlist")
            assert playlist_data is not None
            assert dislike_manager.get_dislike_count() == 1


class TestConcurrentOperations:
    """Tests for concurrent operations and data consistency"""

    def test_multiple_playlist_managers(self, temp_dir, sample_songs):
        """Test multiple playlist managers operating on same directory"""
        manager1 = PlaylistManager(temp_dir)
        manager2 = PlaylistManager(temp_dir)
        
        with patch('builtins.print'):
            # Create playlist with manager1
            manager1.create_playlist("Shared Playlist")
            manager1.add_song_to_playlist("Shared Playlist", sample_songs[0])
            
            # Access with manager2
            playlist_data = manager2.get_playlist("Shared Playlist")
            assert playlist_data is not None
            assert len(playlist_data["songs"]) == 1
            
            # Add song with manager2
            manager2.add_song_to_playlist("Shared Playlist", sample_songs[1])
            
            # Verify with manager1
            updated_playlist = manager1.get_playlist("Shared Playlist")
            assert len(updated_playlist["songs"]) == 2

    def test_multiple_dislike_managers(self, temp_dir, sample_songs):
        """Test multiple dislike managers operating on same file"""
        dislikes_file = os.path.join(temp_dir, "dislikes.json")
        
        manager1 = DislikeManager(dislikes_file)
        manager2 = DislikeManager(dislikes_file)
        
        with patch('builtins.print'):
            # Dislike song with manager1
            manager1.dislike_song(sample_songs[0])
            
            # Check with manager2 (should reload from file)
            manager2._load_dislikes()
            assert manager2.is_disliked("song1")
            
            # Dislike another song with manager2
            manager2.dislike_song(sample_songs[1])
            
            # Check with manager1 (should reload from file)
            manager1._load_dislikes()
            assert manager1.is_disliked("song2")
            assert manager1.get_dislike_count() == 2


class TestDataValidation:
    """Tests for data validation across components"""

    def test_playlist_song_data_validation(self, temp_dir):
        """Test playlist song data validation"""
        playlist_manager = PlaylistManager(temp_dir)
        
        with patch('builtins.print'):
            playlist_manager.create_playlist("Validation Test")
            
            # Test with various song data formats
            valid_song = {
                "videoId": "valid_id",
                "title": "Valid Song",
                "artists": [{"name": "Valid Artist"}]
            }
            
            minimal_song = {
                "videoId": "minimal_id",
                "title": "Minimal Song"
            }
            
            # Both should be handled appropriately
            result1 = playlist_manager.add_song_to_playlist("Validation Test", valid_song)
            result2 = playlist_manager.add_song_to_playlist("Validation Test", minimal_song)
            
            # At least the valid song should be added
            playlist_data = playlist_manager.get_playlist("Validation Test")
            assert len(playlist_data["songs"]) >= 1

    def test_dislike_data_validation(self, temp_dir):
        """Test dislike data validation"""
        dislikes_file = os.path.join(temp_dir, "dislikes.json")
        dislike_manager = DislikeManager(dislikes_file)
        
        with patch('builtins.print'):
            # Test with various song formats
            valid_song = {
                "videoId": "valid_id",
                "title": "Valid Song",
                "artists": [{"name": "Valid Artist"}]
            }
            
            song_without_video_id = {
                "title": "No Video ID",
                "artists": [{"name": "Artist"}]
            }
            
            empty_song = {}
            
            # Valid song should work
            result1 = dislike_manager.dislike_song(valid_song)
            assert result1 is True
            
            # Invalid songs should be rejected gracefully
            result2 = dislike_manager.dislike_song(song_without_video_id)
            assert result2 is False
            
            result3 = dislike_manager.dislike_song(empty_song)
            assert result3 is False
            
            # Only valid song should be disliked
            assert dislike_manager.get_dislike_count() == 1
