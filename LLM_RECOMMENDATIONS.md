# LLM-Powered Music Recommendations

## Overview

The YTM CLI includes an LLM-powered recommendation system that provides intelligent music suggestions based on your listening history and preferences. The system analyzes your recently added songs and disliked tracks to provide personalized, context-aware recommendations.

## Features

### Context-Aware Recommendations

The system automatically considers:
- **Recently added songs**: Top 10 most recently added songs from all playlists
- **Recently disliked songs**: Top 10 most recently disliked tracks
- **User preferences**: Analyzes patterns in your listening history

### Intelligent Filtering

- **Respects dislikes**: Never recommends disliked artists or songs unless explicitly requested
- **Prefers recency**: Prioritizes recently added songs when making recommendations
- **Avoids duplicates**: Won't suggest songs already in your playlists

### Response Structure

Each LLM response includes:
```json
{
  "action": "search|playlist|recommend",
  "query": "search query string",
  "parameters": {
    "limit": 5,
    "playlist": "playlist name (if action=playlist)",
    "notes": "brief explanation of recommendation",
    "fallback": "alternative query if primary fails"
  }
}
```

## Configuration

### LLM Settings (config.ini)

```ini
[llm]
provider = openai          # Options: openai, anthropic
api_key = YOUR_API_KEY     # Your API key
model = gpt-4              # Model to use (gpt-4, gpt-3.5-turbo, claude-3-opus, etc.)
temperature = 0.7          # Response creativity (0.0-1.0)
base_url =                 # Optional: custom API endpoint
```

### Supported Providers

#### OpenAI
- Models: `gpt-4`, `gpt-3.5-turbo`, `gpt-4-turbo`
- Requires: OpenAI API key from https://platform.openai.com/api-keys

#### Anthropic
- Models: `claude-3-opus-20240229`, `claude-3-sonnet-20240229`, `claude-3-haiku-20240307`
- Requires: Anthropic API key from https://console.anthropic.com/

## Usage

### Python API

```python
from ytm_cli.llm_client import LLMClient

# Initialize client
client = LLMClient()

# Get recommendations
response = client.generate("Play something like what I've been listening to lately")

if response:
    print(f"Action: {response.action}")
    print(f"Query: {response.query}")
    print(f"Notes: {response.parameters.get('notes')}")
```

### Testing

Run the test script to see the system in action:

```bash
python test_llm_recommendations.py
```

The test script demonstrates:
- Context loading (recent additions and dislikes)
- Multiple recommendation scenarios
- Response structure and formatting

### Example Requests

**General recommendations:**
```
"Play something like what I've been listening to lately"
→ Analyzes recent additions and suggests similar music
```

**Genre-specific:**
```
"I want some upbeat pop music"
→ Searches for upbeat pop while respecting dislikes
```

**Playlist-based:**
```
"Play my chill playlist"
→ Identifies matching playlist and plays it
```

**Discovery:**
```
"Something new but not from artists I've disliked"
→ Recommends new releases excluding disliked artists
```

**Favorites-based:**
```
"Recommend me 5 songs based on my recent favorites"
→ Analyzes recent additions and suggests similar tracks
```

## How It Works

### 1. Context Collection

When generating recommendations, the system:
- Loads the 10 most recently added songs from all playlists
- Loads the 10 most recently disliked songs
- Formats this data into a structured context

### 2. Prompt Engineering

The system builds a context-aware prompt that includes:
```
Context:
  - Recently added songs (per playlist, newest first):
    - "Song Title" by Artist (playlist: Playlist Name)
    ...
  - Recently disliked songs (newest first):
    - "Song Title" by Artist
    ...

Task:
  Given the user request: "..."
  1. Respect dislikes: never recommend disliked songs/artists
  2. Prefer recency: prioritize recently added songs
  3. Keep it simple: no filler prose

Respond with strict JSON: {...}
```

### 3. LLM Processing

The LLM analyzes:
- User's listening patterns
- Disliked artists and songs
- Recent preferences
- Request intent

### 4. Structured Response

Returns a JSON object with:
- **action**: Type of recommendation (search/playlist/recommend)
- **query**: Specific search query or playlist name
- **parameters**: Additional context including notes and fallback options

## API Methods

### `LLMClient.__init__(playlists_dir, dislikes_file)`

Initialize the LLM client.

**Parameters:**
- `playlists_dir` (str): Path to playlists directory (default: "playlists")
- `dislikes_file` (str): Path to dislikes JSON file (default: "dislikes.json")

### `LLMClient.generate(prompt, verbose=False)`

Generate a recommendation based on user prompt.

**Parameters:**
- `prompt` (str): User's music request
- `verbose` (bool): If True, prints the context prompt being sent

**Returns:**
- `LLMResponse` object or `None` on error

### `LLMClient.get_context_summary()`

Get a summary of current context for debugging.

**Returns:**
- Dictionary with recent additions and dislikes

**Example:**
```python
context = client.get_context_summary()
print(f"Recent additions: {context['recent_added_count']}")
print(f"Recent dislikes: {context['recent_disliked_count']}")
```

## Response Actions

### `search`
Direct search query for YouTube Music.
- Used when user wants to discover new music
- Query is optimized based on context

### `playlist`
Play an existing local playlist.
- Used when user references a specific playlist
- Parameters include playlist name

### `recommend`
Generate personalized recommendations.
- Used for context-aware suggestions
- Query describes the recommendation criteria

## Best Practices

1. **Keep API keys secure**: Never commit API keys to version control
2. **Set appropriate temperature**: Lower values (0.3-0.5) for more consistent results
3. **Use verbose mode**: Enable verbose logging during testing
4. **Monitor API usage**: LLM calls consume API credits
5. **Handle errors gracefully**: Always check for `None` response

## Troubleshooting

### Issue: "LLM Error: Unauthorized"
- **Cause**: Invalid API key
- **Solution**: Verify API key in `config.ini` is correct and active

### Issue: "LLM Error: Model not found"
- **Cause**: Specified model doesn't exist or no access
- **Solution**: Use a supported model (gpt-4, gpt-3.5-turbo, etc.)

### Issue: No context data
- **Cause**: Empty playlists or dislikes
- **Solution**: Add some songs to playlists and dislike a few tracks first

### Issue: JSON parsing error
- **Cause**: LLM returned invalid JSON
- **Solution**: Adjust temperature lower or try a different model

## Data Privacy

- All playlist and dislike data stays **local**
- Only song metadata (title, artist, playlist name) is sent to the LLM
- No audio files or personal data is transmitted
- API calls follow provider's privacy policies

## Future Enhancements

Potential improvements:
- Integration with ytm_cli main search flow
- Command-line interface for recommendations
- Caching frequently used recommendations
- Multi-turn conversations for refinement
- Support for more LLM providers (local models, etc.)

## Example Output

```
🎵 User Request: Play something like what I've been listening to lately

📋 LLM Response:
  Action: recommend
  Query: Vietnamese pop music and international pop ballads
  Parameters:
    • limit: 5
    • notes: User has recently listened to a mix of Vietnamese pop songs and 
      international pop ballads.
    • fallback: Latest pop hits
```

## License

This feature follows the same license as the main YTM CLI project (see LICENSE file).
