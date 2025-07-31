"""Local playlist management for YTM CLI"""

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from rich import print


class PlaylistManager:
    """Manages local playlists stored as JSON files"""

    def __init__(self, playlists_dir: str = "playlists"):
        self.playlists_dir = playlists_dir
        self.ensure_playlists_dir()

    def ensure_playlists_dir(self):
        """Create playlists directory if it doesn't exist"""
        if not os.path.exists(self.playlists_dir):
            os.makedirs(self.playlists_dir)

    def create_playlist(self, name: str, description: str = "") -> bool:
        """Create a new playlist"""
        try:
            safe_name = self._safe_filename(name)
            playlist_path = os.path.join(self.playlists_dir, f"{safe_name}.json")

            if os.path.exists(playlist_path):
                print(f"[red]Playlist '{name}' already exists[/red]")
                return False

            playlist_data = {
                "name": name,
                "description": description,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "songs": [],
            }

            with open(playlist_path, "w", encoding="utf-8") as f:
                json.dump(playlist_data, f, indent=2, ensure_ascii=False)

            print(f"[green]✅ Created playlist: {name}[/green]")
            return True

        except (IOError, OSError) as e:
            print(f"[red]Error creating playlist: {e}[/red]")
            return False

    def add_song_to_playlist(self, playlist_name: str, song: Dict[str, Any]) -> bool:
        """Add a song to an existing playlist"""
        try:
            playlist_path = self._get_playlist_path(playlist_name)
            if not playlist_path:
                print(f"[red]Playlist '{playlist_name}' not found[/red]")
                return False

            # Load existing playlist
            with open(playlist_path, "r", encoding="utf-8") as f:
                playlist_data = json.load(f)

            # Create song entry with essential info
            song_entry = {
                "title": song.get("title", "Unknown"),
                "artist": song.get("artists", [{}])[0].get("name", "Unknown Artist"),
                "videoId": song.get("videoId", ""),
                "duration": song.get("duration_seconds", song.get("duration", "")),
                "album": (
                    song.get("album", {}).get("name", "") if song.get("album") else ""
                ),
                "added_at": datetime.now().isoformat(),
            }

            # Check if song already exists (by videoId)
            existing_song = next(
                (
                    s
                    for s in playlist_data["songs"]
                    if s.get("videoId") == song_entry["videoId"]
                ),
                None,
            )
            if existing_song:
                print(
                    f"[yellow]Song already in playlist: {song_entry['title']}[/yellow]"
                )
                return False

            # Add song and update timestamp
            playlist_data["songs"].append(song_entry)
            playlist_data["updated_at"] = datetime.now().isoformat()

            # Save updated playlist
            with open(playlist_path, "w", encoding="utf-8") as f:
                json.dump(playlist_data, f, indent=2, ensure_ascii=False)

            print(
                f"[green]✅ Added '{song_entry['title']}' to '{playlist_name}'[/green]"
            )
            return True

        except (IOError, OSError, json.JSONDecodeError) as e:
            print(f"[red]Error adding song to playlist: {e}[/red]")
            return False

    def list_playlists(self) -> List[Dict[str, Any]]:
        """List all available playlists"""
        playlists = []

        try:
            if not os.path.exists(self.playlists_dir):
                return playlists

            for filename in os.listdir(self.playlists_dir):
                if filename.endswith(".json"):
                    playlist_path = os.path.join(self.playlists_dir, filename)
                    try:
                        with open(playlist_path, "r", encoding="utf-8") as f:
                            playlist_data = json.load(f)

                        playlists.append(
                            {
                                "name": playlist_data.get("name", filename[:-5]),
                                "description": playlist_data.get("description", ""),
                                "song_count": len(playlist_data.get("songs", [])),
                                "created_at": playlist_data.get("created_at", ""),
                                "updated_at": playlist_data.get("updated_at", ""),
                                "filename": filename,
                            }
                        )
                    except (IOError, OSError, json.JSONDecodeError) as e:
                        print(
                            f"[yellow]Warning: Could not load playlist {filename}: {e}[/yellow]"
                        )
                        continue

            # Sort by creation date (newest first)
            playlists.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return playlists

        except (IOError, OSError) as e:
            print(f"[red]Error listing playlists: {e}[/red]")
            return []

    def get_playlist(self, playlist_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific playlist by name"""
        try:
            playlist_path = self._get_playlist_path(playlist_name)
            if not playlist_path:
                return None

            with open(playlist_path, "r", encoding="utf-8") as f:
                return json.load(f)

        except (IOError, OSError, json.JSONDecodeError) as e:
            print(f"[red]Error loading playlist: {e}[/red]")
            return None

    def delete_playlist(self, playlist_name: str) -> bool:
        """Delete a playlist"""
        try:
            playlist_path = self._get_playlist_path(playlist_name)
            if not playlist_path:
                print(f"[red]Playlist '{playlist_name}' not found[/red]")
                return False

            os.remove(playlist_path)
            print(f"[green]✅ Deleted playlist: {playlist_name}[/green]")
            return True

        except (IOError, OSError) as e:
            print(f"[red]Error deleting playlist: {e}[/red]")
            return False

    def remove_song_from_playlist(self, playlist_name: str, song_index: int) -> bool:
        """Remove a song from playlist by index"""
        try:
            playlist_path = self._get_playlist_path(playlist_name)
            if not playlist_path:
                print(f"[red]Playlist '{playlist_name}' not found[/red]")
                return False

            with open(playlist_path, "r", encoding="utf-8") as f:
                playlist_data = json.load(f)

            songs = playlist_data.get("songs", [])
            if song_index < 0 or song_index >= len(songs):
                print(f"[red]Invalid song index: {song_index}[/red]")
                return False

            removed_song = songs.pop(song_index)
            playlist_data["updated_at"] = datetime.now().isoformat()

            with open(playlist_path, "w", encoding="utf-8") as f:
                json.dump(playlist_data, f, indent=2, ensure_ascii=False)

            print(
                f"[green]✅ Removed '{removed_song['title']}' from '{playlist_name}'[/green]"
            )
            return True

        except (IOError, OSError, json.JSONDecodeError) as e:
            print(f"[red]Error removing song from playlist: {e}[/red]")
            return False

    def remove_song_from_playlist_by_id(self, playlist_name: str, video_id: str) -> bool:
        """Remove a song from playlist by video ID"""
        try:
            playlist_path = self._get_playlist_path(playlist_name)
            if not playlist_path:
                return False

            with open(playlist_path, "r", encoding="utf-8") as f:
                playlist_data = json.load(f)

            songs = playlist_data.get("songs", [])
            original_count = len(songs)
            
            # Remove songs with matching video ID
            playlist_data["songs"] = [
                song for song in songs 
                if song.get("videoId") != video_id
            ]
            
            # Check if any songs were removed
            if len(playlist_data["songs"]) == original_count:
                # No songs were removed (song not in playlist)
                return False
            
            playlist_data["updated_at"] = datetime.now().isoformat()

            with open(playlist_path, "w", encoding="utf-8") as f:
                json.dump(playlist_data, f, indent=2, ensure_ascii=False)

            return True

        except (IOError, OSError, json.JSONDecodeError) as e:
            print(f"[red]Error removing song from playlist: {e}[/red]")
            return False

    def get_playlist_names(self) -> List[str]:
        """Get list of playlist names for quick selection"""
        playlists = self.list_playlists()
        return [p["name"] for p in playlists]

    def _safe_filename(self, name: str) -> str:
        """Convert playlist name to safe filename"""
        # Remove or replace problematic characters
        safe_name = re.sub(r'[<>:"/\\|?*]', "_", name)
        safe_name = safe_name.strip(". ")  # Remove leading/trailing dots and spaces
        return safe_name or "unnamed_playlist"

    def _get_playlist_path(self, playlist_name: str) -> Optional[str]:
        """Get the file path for a playlist by name"""
        # Try exact safe filename match first
        safe_name = self._safe_filename(playlist_name)
        exact_path = os.path.join(self.playlists_dir, f"{safe_name}.json")

        if os.path.exists(exact_path):
            return exact_path

        # Fallback: search by actual playlist name in file content
        try:
            for filename in os.listdir(self.playlists_dir):
                if filename.endswith(".json"):
                    filepath = os.path.join(self.playlists_dir, filename)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        if data.get("name", "").lower() == playlist_name.lower():
                            return filepath
                    except (json.JSONDecodeError, FileNotFoundError):
                        continue
        except (IOError, OSError):
            pass

        return None


# Global playlist manager instance
playlist_manager = PlaylistManager()
