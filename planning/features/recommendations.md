# AI-Powered Recommendation System

## Core Features

### 1. Smart Radio Generation
- **Current**: Basic YTMusic radio based on seed song
- **Enhanced**: AI analyzes user's listening history, likes/dislikes, and current mood to generate personalized radio stations
- **Implementation**: Use AI to analyze user preferences and generate seed combinations

### 2. Mood-Based Recommendations
- **Feature**: Detect user's mood from listening patterns and suggest appropriate music
- **Triggers**:
  - Time of day (energetic morning, calm evening)
  - Weather integration (rainy day vibes)
  - Recent listening patterns (heavy metal → suggest more intense music)
- **UI**: `python -m ytm_cli mood [happy|sad|energetic|calm|focus]`

### 3. Discovery Engine
- **Feature**: AI-curated music discovery based on user's taste expansion
- **Logic**: Find songs that are 70% similar to user's taste + 30% new exploration
- **UI**: `python -m ytm_cli discover` - daily curated playlist

### 4. Context-Aware Suggestions
- **Feature**: Recommendations based on current context
- **Contexts**:
  - Time of day
  - Day of week
  - Season
  - Recently played artists/genres
  - Current playlist being played

### 5. Natural Language Search
- **Current**: Simple keyword search
- **Enhanced**: "Play something like Radiohead but more upbeat" or "I want sad songs from the 90s"
- **Implementation**: AI interprets natural language and generates appropriate search queries

### 6. Smart Playlist Continuation
- **Feature**: When a playlist ends, AI suggests what to play next
- **Logic**: Analyze playlist's musical characteristics and user's current state
- **UI**: Automatic suggestion with option to accept/decline

## AI Model Responsibilities

### Claude/GPT Integration
- **Music taste analysis**: Process user's listening history to understand preferences
- **Natural language processing**: Interpret user's mood/context requests
- **Playlist curation**: Generate thematic playlists based on prompts

### Gemini Integration
- **Real-time analysis**: Quick mood detection from recent plays
- **Pattern recognition**: Identify listening patterns and habits
- **Contextual awareness**: Time-based and situational recommendations

## Data Sources for AI

1. **Listening History**: All played songs with timestamps
2. **User Actions**: Likes, dislikes, skips, replays, playlist additions
3. **Session Data**: Time spent listening, session lengths, interruption patterns
4. **Playlist Analysis**: User-created playlists and their characteristics
5. **Search History**: What users search for vs. what they actually play

## Implementation Architecture

```
User Input → AI Model → YTMusic API → Filtered Results → User
     ↑                                                      ↓
     └── Feedback Loop ← User Actions ← Playback Data ←─────┘
```

## Privacy Considerations

- All AI processing can be done locally or with user consent
- Option to disable AI features entirely
- Clear data usage policies
- User control over data retention