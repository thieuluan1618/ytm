"""Dislike management for YTM CLI - tracks and filters disliked songs"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List

from rich import print


class DislikeManager:
    """Manages disliked songs stored in JSON file"""

    def __init__(self, dislikes_file: str = "dislikes.json"):
        self.dislikes_file = dislikes_file
        self._disliked_ids = set()
        self._load_dislikes()

    def _load_dislikes(self):
        """Load disliked song IDs from file"""
        try:
            if os.path.exists(self.dislikes_file):
                with open(self.dislikes_file, encoding="utf-8") as f:
                    data = json.load(f)
                    self._disliked_ids = {
                        song.get("videoId", "")
                        for song in data.get("songs", [])
                        if song.get("videoId")
                    }
        except Exception as e:
            print(f"[yellow]Warning: Could not load dislikes: {e}[/yellow]")
            self._disliked_ids = set()

    def _save_dislikes(self, songs_data: List[Dict[str, Any]]):
        """Save disliked songs data to file"""
        try:
            data = {
                "updated_at": datetime.now().isoformat(),
                "count": len(songs_data),
                "songs": songs_data,
            }
            with open(self.dislikes_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[red]Error saving dislikes: {e}[/red]")

    def dislike_song(self, song: Dict[str, Any]) -> bool:
        """Add a song to dislikes"""
        try:
            video_id = song.get("videoId", "")
            if not video_id:
                print("[red]Cannot dislike song: missing videoId[/red]")
                return False

            if video_id in self._disliked_ids:
                print("[yellow]Song is already disliked[/yellow]")
                return False

            # Load existing dislikes
            existing_songs = []
            if os.path.exists(self.dislikes_file):
                try:
                    with open(self.dislikes_file, encoding="utf-8") as f:
                        data = json.load(f)
                        existing_songs = data.get("songs", [])
                except (json.JSONDecodeError, FileNotFoundError):
                    pass

            # Create dislike entry
            dislike_entry = {
                "title": song.get("title", "Unknown"),
                "artist": (
                    song.get("artists", [{}])[0].get("name", "Unknown Artist")
                    if song.get("artists")
                    else "Unknown Artist"
                ),
                "videoId": video_id,
                "duration": song.get("duration_seconds", song.get("duration", "")),
                "album": (song.get("album", {}).get("name", "") if song.get("album") else ""),
                "disliked_at": datetime.now().isoformat(),
            }

            # Add to list and save
            existing_songs.append(dislike_entry)
            self._save_dislikes(existing_songs)
            self._disliked_ids.add(video_id)

            title = dislike_entry["title"]
            artist = dislike_entry["artist"]
            print(f"[red]👎 Disliked: {title} - {artist}[/red]")
            print(
                "[yellow]This song will be skipped in future searches and radio playlists[/yellow]"
            )
            return True

        except Exception as e:
            print(f"[red]Error disliking song: {e}[/red]")
            return False

    def is_disliked(self, video_id: str) -> bool:
        """Check if a song is disliked"""
        return video_id in self._disliked_ids

    def filter_disliked_songs(self, songs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter out disliked songs from a list"""
        if not self._disliked_ids:
            return songs

        filtered = []
        filtered_count = 0

        for song in songs:
            video_id = song.get("videoId", "")
            if video_id and video_id in self._disliked_ids:
                filtered_count += 1
                continue
            filtered.append(song)

        if filtered_count > 0:
            print(f"[yellow]Filtered out {filtered_count} disliked song(s)[/yellow]")

        return filtered

    def get_disliked_songs(self) -> List[Dict[str, Any]]:
        """Get all disliked songs"""
        try:
            if not os.path.exists(self.dislikes_file):
                return []

            with open(self.dislikes_file, encoding="utf-8") as f:
                data = json.load(f)
                return data.get("songs", [])
        except Exception as e:
            print(f"[red]Error loading disliked songs: {e}[/red]")
            return []

    def remove_dislike(self, video_id: str) -> bool:
        """Remove a song from dislikes"""
        try:
            if video_id not in self._disliked_ids:
                return False

            songs = self.get_disliked_songs()
            filtered_songs = [s for s in songs if s.get("videoId") != video_id]

            self._save_dislikes(filtered_songs)
            self._disliked_ids.discard(video_id)

            print("[green]Removed song from dislikes[/green]")
            return True

        except Exception as e:
            print(f"[red]Error removing dislike: {e}[/red]")
            return False

    def clear_all_dislikes(self) -> bool:
        """Clear all dislikes"""
        try:
            if os.path.exists(self.dislikes_file):
                os.remove(self.dislikes_file)
            self._disliked_ids.clear()
            print("[green]All dislikes cleared[/green]")
            return True
        except Exception as e:
            print(f"[red]Error clearing dislikes: {e}[/red]")
            return False

    def get_dislike_count(self) -> int:
        """Get count of disliked songs"""
        return len(self._disliked_ids)


# Global dislike manager instance
dislike_manager = DislikeManager()
