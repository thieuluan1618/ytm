"""
Lyrics service module for fetching timestamped lyrics from LRCLIB API
"""

import re

import requests


class LyricsService:
    """Service for fetching timestamped lyrics from LRCLIB API"""

    def __init__(self, user_agent: str = "ytm-cli/0.3.0"):
        self.base_url = "https://lrclib.net/api"
        self.user_agent = user_agent
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})

    def get_lyrics(
        self,
        track_name: str,
        artist_name: str,
        album_name: str = None,
        duration: int = None,
    ) -> dict | None:
        """
        Get lyrics by track details

        Args:
            track_name: Name of the track
            artist_name: Name of the artist
            album_name: Name of the album (optional)
            duration: Duration in seconds (optional)

        Returns:
            Dict with lyrics data or None if not found
        """
        params = {"track_name": track_name, "artist_name": artist_name}

        if album_name:
            params["album_name"] = album_name
        if duration:
            params["duration"] = duration

        try:
            response = self.session.get(f"{self.base_url}/get", params=params, timeout=5)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return None
            else:
                return None
        except requests.RequestException:
            return None

    def search_lyrics(self, track_name: str) -> list[dict]:
        """
        Search for lyrics by track name

        Args:
            track_name: Name of the track to search

        Returns:
            List of matching lyrics
        """
        params = {"track_name": track_name}

        try:
            response = self.session.get(f"{self.base_url}/search", params=params, timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                return []
        except requests.RequestException:
            return []


class LRCParser:
    """Parser for LRC format lyrics with timestamps"""

    @staticmethod
    def parse_lrc(lrc_content: str) -> list[tuple[float, str]]:
        """
        Parse LRC format lyrics into list of (timestamp, text) tuples

        Args:
            lrc_content: LRC format lyrics string

        Returns:
            List of (timestamp_seconds, line_text) tuples sorted by timestamp
        """
        if not lrc_content:
            return []

        lines = []
        lrc_pattern = r"\[(\d+):(\d{2})(?:\.(\d{1,3}))?\]"

        for line in lrc_content.split("\n"):
            line = line.strip()
            if not line:
                continue

            matches = list(re.finditer(lrc_pattern, line))
            text = re.sub(lrc_pattern, "", line).strip()
            for match in matches:
                minutes = int(match.group(1))
                seconds = int(match.group(2))
                centiseconds = int(
                    (match.group(3) or "0").ljust(3, "0")[:3]
                )  # Handle 2 or 3 digit centiseconds

                # Convert to total seconds
                timestamp = minutes * 60 + seconds + centiseconds / 1000.0
                lines.append((timestamp, text))

        # Sort by timestamp
        lines.sort(key=lambda x: x[0])
        return lines

    @staticmethod
    def get_current_line_index(parsed_lyrics: list[tuple[float, str]], current_time: float) -> int:
        """
        Get the index of the current line based on playback time

        Args:
            parsed_lyrics: List of (timestamp, text) tuples
            current_time: Current playback time in seconds

        Returns:
            Index of current line, or -1 if no line should be highlighted
        """
        if not parsed_lyrics or current_time < 0:
            return -1

        current_index = -1
        for i, (timestamp, _) in enumerate(parsed_lyrics):
            if current_time >= timestamp:
                current_index = i
            else:
                break

        return current_index


def get_song_metadata_from_item(item: dict) -> tuple[str, str, str, int]:
    """
    Extract metadata from YouTube Music item for lyrics search

    Args:
        item: YouTube Music song item

    Returns:
        Tuple of (track_name, artist_name, album_name, duration)
    """
    track_name = item.get("title", "")

    # Extract artist name
    artist_name = ""
    if "artists" in item and item["artists"]:
        artist_name = item["artists"][0].get("name", "")

    # Extract album name
    album_name = ""
    if "album" in item and item["album"]:
        if isinstance(item["album"], dict):
            album_name = item["album"].get("name", "")
        else:
            album_name = str(item["album"])

    # Extract duration (convert to seconds if needed)
    duration = 0
    try:
        duration = int(item.get("duration_seconds") or 0)
    except (TypeError, ValueError, OverflowError):
        pass
    if not duration:
        duration_str = item.get("duration")
        if isinstance(duration_str, str) and ":" in duration_str:
            try:
                parts = duration_str.split(":")
                if len(parts) in (2, 3):
                    for part in parts:
                        duration = duration * 60 + int(part)
            except ValueError:
                duration = 0

    return track_name, artist_name, album_name, duration


def get_playback_lyrics(item: dict) -> dict | None:
    """Use identical lookup metadata for terminal and desktop lyrics."""
    title = item.get("title", "")
    artists = item.get("artists") or []
    artist = artists[0].get("name") if artists else None
    if artist == "Unknown Artist":
        artist = None
    if not artist and " - " in title:
        title, artist = title.split(" - ", 1)
    song = {"title": title, "videoId": item.get("videoId")}
    if artist:
        song["artists"] = [{"name": artist}]
    return get_timestamped_lyrics(song)


def get_timestamped_lyrics(item: dict) -> dict | None:
    """
    Get timestamped lyrics for a YouTube Music item

    Args:
        item: YouTube Music song item

    Returns:
        Dict with 'synced_lyrics', 'plain_lyrics', 'parsed_lyrics' keys or None
    """
    track_name, artist_name, album_name, duration = get_song_metadata_from_item(item)

    if not track_name or not artist_name:
        return None

    lyrics_service = LyricsService()

    # Try exact match first
    lyrics_data = lyrics_service.get_lyrics(track_name, artist_name, album_name, duration)

    # Radio metadata can describe a different release or video duration. Match
    # the terminal viewer's title/artist lookup before trying a broad search.
    if (album_name or duration) and (not lyrics_data or not lyrics_data.get("syncedLyrics")):
        relaxed_data = lyrics_service.get_lyrics(track_name, artist_name)
        if relaxed_data and (relaxed_data.get("syncedLyrics") or not lyrics_data):
            lyrics_data = relaxed_data

    # If no exact match, try search
    if not lyrics_data:
        search_results = lyrics_service.search_lyrics(track_name)
        if search_results:
            # Use the first result
            lyrics_data = search_results[0]

    if not lyrics_data:
        return None

    # Parse LRC lyrics if available
    parsed_lyrics = []
    if lyrics_data.get("syncedLyrics"):
        parsed_lyrics = LRCParser.parse_lrc(lyrics_data["syncedLyrics"])

    return {
        "synced_lyrics": lyrics_data.get("syncedLyrics", ""),
        "plain_lyrics": lyrics_data.get("plainLyrics", ""),
        "parsed_lyrics": parsed_lyrics,
        "source": "LRCLIB",
    }
