"""LLM client wrapper for YTM CLI"""

import json
import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional

import requests

from .config import get_config_value

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    action: str  # "search", "playlist", "recommend", "create_playlist", etc.
    query: str
    parameters: dict = field(default_factory=dict)  # Additional parameters like limit, filters, notes, fallback, etc.
    songs: List[dict] = field(default_factory=list)  # For create_playlist: list of {"title": ..., "artist": ...}


def _load_vertex_credentials():
    """Auto-detect vertex-ai-client.json and set GOOGLE_APPLICATION_CREDENTIALS."""
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        return
    # Search relative to project root (two levels up from this file)
    project_root = os.path.join(os.path.dirname(__file__), "..")
    cred_path = os.path.abspath(os.path.join(project_root, "vertex-ai-client.json"))
    if os.path.exists(cred_path):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cred_path
        logger.info("Loaded credentials from: %s", cred_path)


class LLMClient:
    def __init__(self, playlists_dir: str = "playlists", dislikes_file: str = "dislikes.json"):
        self.provider = get_config_value("llm", "provider", "openai")
        self.api_key = get_config_value("llm", "api_key")
        self.model = get_config_value("llm", "model", "gemini-2.5-pro")
        self.temperature = float(get_config_value("llm", "temperature", "0.7"))
        self.base_url = get_config_value("llm", "base_url", None)
        self.playlists_dir = playlists_dir
        self.dislikes_file = dislikes_file

    def _get_recent_playlist_additions(self, limit: int = 10) -> List[dict]:
        """Get recently added songs from all playlists"""
        recent_songs = []

        try:
            if not os.path.exists(self.playlists_dir):
                return recent_songs

            for filename in os.listdir(self.playlists_dir):
                if not filename.endswith(".json"):
                    continue

                playlist_path = os.path.join(self.playlists_dir, filename)
                try:
                    with open(playlist_path, encoding="utf-8") as f:
                        playlist_data = json.load(f)

                    playlist_name = playlist_data.get("name", filename[:-5])
                    songs = playlist_data.get("songs", [])

                    for song in songs:
                        recent_songs.append({
                            "title": song.get("title", "Unknown"),
                            "artist": song.get("artist", "Unknown Artist"),
                            "added_at": song.get("added_at", ""),
                            "playlist": playlist_name
                        })
                except Exception:
                    continue

            # Sort by added_at timestamp (newest first)
            recent_songs.sort(key=lambda x: x.get("added_at", ""), reverse=True)
            return recent_songs[:limit]

        except Exception:
            return []

    def _get_recent_dislikes(self, limit: int = 10) -> List[dict]:
        """Get recently disliked songs"""
        try:
            if not os.path.exists(self.dislikes_file):
                return []

            with open(self.dislikes_file, encoding="utf-8") as f:
                data = json.load(f)
                songs = data.get("songs", [])

            # Sort by disliked_at timestamp (newest first)
            songs.sort(key=lambda x: x.get("disliked_at", ""), reverse=True)

            recent = []
            for song in songs[:limit]:
                recent.append({
                    "title": song.get("title", "Unknown"),
                    "artist": song.get("artist", "Unknown Artist"),
                    "disliked_at": song.get("disliked_at", "")
                })

            return recent

        except Exception:
            return []

    def _build_context_prompt(self, user_prompt: str) -> str:
        """Build context-aware prompt with recent songs and dislikes"""
        recent_added = self._get_recent_playlist_additions()
        recent_disliked = self._get_recent_dislikes()

        # Format recent additions
        added_context = ""
        if recent_added:
            added_lines = []
            for song in recent_added:
                added_lines.append(f"  - \"{song['title']}\" by {song['artist']} (playlist: {song['playlist']})")
            added_context = "\n".join(added_lines)
        else:
            added_context = "  (none)"

        # Format recent dislikes
        disliked_context = ""
        if recent_disliked:
            disliked_lines = []
            for song in recent_disliked:
                disliked_lines.append(f"  - \"{song['title']}\" by {song['artist']}")
            disliked_context = "\n".join(disliked_lines)
        else:
            disliked_context = "  (none)"

        return f"""Context:
  - Recently added songs (per playlist, newest first):
{added_context}
  - Recently disliked songs (newest first):
{disliked_context}

Task:
  Given the user request: "{user_prompt}"

  1. Respect dislikes: never recommend or queue a disliked song/artist unless explicitly asked to review dislikes.
  2. Prefer recency: prioritize songs added most recently when the request fits their style, but avoid duplicate suggestions.
  3. Keep it simple: no filler prose, no markdown, no code blocks.

  Respond with strict JSON:
  {{
    "action": "<search|playlist|recommend>",
    "query": "<string>",
    "parameters": {{
      "limit": <int, optional>,
      "playlist": "<name if action=playlist>",
      "notes": "<brief reason referencing context>",
      "fallback": "<alternative query if primary fails>"
    }}
  }}

  If the request cannot be satisfied, set action to "search" with a safe generic query and explain in "notes". Only output JSON—no additional text."""

    def _build_create_playlist_prompt(self, user_prompt: str, num_songs: int = 15) -> str:
        """Build prompt for AI playlist creation"""
        recent_added = self._get_recent_playlist_additions()
        recent_disliked = self._get_recent_dislikes()

        added_context = "  (none)"
        if recent_added:
            added_lines = [
                f'  - "{s["title"]}" by {s["artist"]}' for s in recent_added
            ]
            added_context = "\n".join(added_lines)

        disliked_context = "  (none)"
        if recent_disliked:
            disliked_lines = [
                f'  - "{s["title"]}" by {s["artist"]}' for s in recent_disliked
            ]
            disliked_context = "\n".join(disliked_lines)

        return f"""Context:
  - Songs the user already likes:
{added_context}
  - Songs/artists the user dislikes (NEVER include these):
{disliked_context}

Task:
  The user wants to create a playlist: "{user_prompt}"

  Generate exactly {num_songs} songs that match this request.
  - Each song must be a real, existing song with correct title and artist.
  - Avoid disliked artists/songs.
  - Include a mix of popular and fitting deep cuts.
  - Suggest a short, catchy playlist name.

  Respond with strict JSON only:
  {{
    "playlist_name": "<short catchy name>",
    "songs": [
      {{"title": "<song title>", "artist": "<artist name>"}},
      ...
    ]
  }}

  Only output JSON—no additional text."""

    def generate_playlist(self, prompt: str, num_songs: int = 15, verbose: bool = False) -> Optional[LLMResponse]:
        """Generate a playlist of songs from LLM based on a description"""
        try:
            context_prompt = self._build_create_playlist_prompt(prompt, num_songs)

            if verbose:
                print("\n[dim]--- Create Playlist Prompt ---[/dim]")
                print(context_prompt)
                print("[dim]--- End Prompt ---[/dim]\n")

            if self.provider == "google":
                result = self._call_google(context_prompt)
            elif self.provider == "openai":
                result = self._call_openai(context_prompt)
            elif self.provider == "anthropic":
                result = self._call_anthropic(context_prompt)
            else:
                raise ValueError(f"Unsupported LLM provider: {self.provider}")

            # Parse the playlist response
            return LLMResponse(
                action="create_playlist",
                query=result.parameters.get("playlist_name", prompt),
                parameters=result.parameters,
                songs=result.parameters.get("songs", []),
            )
        except Exception as e:
            print(f"[red]LLM Error: {str(e)}[/red]")
            return None

    def get_context_summary(self) -> dict:
        """Get a summary of current context for debugging"""
        recent_added = self._get_recent_playlist_additions()
        recent_disliked = self._get_recent_dislikes()

        return {
            "recent_added_count": len(recent_added),
            "recent_disliked_count": len(recent_disliked),
            "recent_added": recent_added,
            "recent_disliked": recent_disliked
        }

    def generate(self, prompt: str, verbose: bool = False) -> Optional[LLMResponse]:
        """Send prompt to LLM and return structured response with context

        Args:
            prompt: User's music request
            verbose: If True, print the context prompt being sent
        """
        try:
            context_prompt = self._build_context_prompt(prompt)

            if verbose:
                print("\n[dim]--- Context Prompt ---[/dim]")
                print(context_prompt)
                print("[dim]--- End Context Prompt ---[/dim]\n")

            if self.provider == "google":
                return self._call_google(context_prompt)
            elif self.provider == "openai":
                return self._call_openai(context_prompt)
            elif self.provider == "anthropic":
                return self._call_anthropic(context_prompt)
            else:
                raise ValueError(f"Unsupported LLM provider: {self.provider}")
        except Exception as e:
            print(f"[red]LLM Error: {str(e)}[/red]")
            return None

    def _extract_json(self, text: str) -> dict:
        """Extract JSON from LLM response, handling markdown code blocks."""
        text = text.strip()
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            text = text[start:end].strip()
        elif text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
        return json.loads(text)

    def _call_google(self, prompt: str) -> LLMResponse:
        """Call Google Vertex AI (Gemini) using service account credentials."""
        from google import genai

        _load_vertex_credentials()

        # Read project ID from credentials file
        project = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        if not project and os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            with open(os.getenv("GOOGLE_APPLICATION_CREDENTIALS")) as f:
                project = json.load(f).get("project_id")

        if not project:
            raise ValueError(
                "Set GOOGLE_APPLICATION_CREDENTIALS or place vertex-ai-client.json in project root"
            )

        client = genai.Client(vertexai=True, project=project, location=location)

        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={
                "temperature": self.temperature,
                "system_instruction": "You are a music recommendation assistant. You provide structured JSON responses based on user context and preferences. Never recommend disliked artists or songs.",
            },
        )

        content = self._extract_json(response.text)

        # Handle both regular action responses and playlist generation responses
        if "songs" in content and "playlist_name" in content:
            return LLMResponse(
                action="create_playlist",
                query=content["playlist_name"],
                parameters=content,
                songs=content["songs"],
            )

        return LLMResponse(
            action=content.get("action", "search"),
            query=content.get("query", ""),
            parameters=content.get("parameters", {}),
        )

    def _call_openai(self, prompt: str) -> LLMResponse:
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a music recommendation assistant. You provide structured JSON responses based on user context and preferences. Never recommend disliked artists or songs."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": self.temperature,
        }

        response = requests.post(
            f"{self.base_url or 'https://api.openai.com/v1'}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            error_detail = response.text
            raise Exception(f"{str(e)}: {error_detail}") from e

        response_text = response.json()["choices"][0]["message"]["content"].strip()
        content = self._extract_json(response_text)

        if "songs" in content and "playlist_name" in content:
            return LLMResponse(
                action="create_playlist",
                query=content["playlist_name"],
                parameters=content,
                songs=content["songs"],
            )

        return LLMResponse(
            action=content["action"],
            query=content["query"],
            parameters=content.get("parameters", {}),
        )

    def _call_anthropic(self, prompt: str) -> LLMResponse:
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

        payload = {
            "model": self.model,
            "system": "You are a music recommendation assistant. You provide structured JSON responses based on user context and preferences. Never recommend disliked artists or songs.",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": self.temperature,
            "max_tokens": 500,
        }

        response = requests.post(
            f"{self.base_url or 'https://api.anthropic.com/v1'}/messages",
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()

        content = self._extract_json(response.json()["content"][0]["text"])

        if "songs" in content and "playlist_name" in content:
            return LLMResponse(
                action="create_playlist",
                query=content["playlist_name"],
                parameters=content,
                songs=content["songs"],
            )

        return LLMResponse(
            action=content["action"],
            query=content["query"],
            parameters=content.get("parameters", {}),
        )
