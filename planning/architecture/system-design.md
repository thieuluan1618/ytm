# Phase 2 System Architecture

## High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User Input    │    │   AI Engine     │    │  Data Storage   │
│                 │    │                 │    │                 │
│ • CLI Commands  │◄──►│ • Claude/OpenAI │◄──►│ • SQLite DB     │
│ • Voice Input   │    │ • Gemini        │    │ • JSON Files    │
│ • Key Controls  │    │ • Local ML      │    │ • User Prefs    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Music Engine   │    │  Analytics      │    │  External APIs  │
│                 │    │                 │    │                 │
│ • YTMusic API   │◄──►│ • Usage Stats   │◄──►│ • Weather API   │
│ • MPV Player    │    │ • Patterns      │    │ • Calendar API  │
│ • Queue Mgmt    │    │ • Insights      │    │ • Social APIs   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Core Components

### 1. AI Engine (`ytm_cli/ai/`)

```
ai/
├── __init__.py
├── models/
│   ├── claude.py      # Claude integration
│   ├── openai.py      # OpenAI integration
│   ├── gemini.py      # Gemini integration
│   └── local.py       # Local ML models
├── processors/
│   ├── recommendations.py  # Music recommendation logic
│   ├── nlp.py             # Natural language processing
│   ├── mood.py            # Mood detection/analysis
│   └── patterns.py        # Pattern recognition
└── prompts/
    ├── recommendation_prompts.py
    ├── mood_prompts.py
    └── discovery_prompts.py
```

### 2. Data Layer (`ytm_cli/data/`)

```
data/
├── __init__.py
├── models.py          # Data models (SQLAlchemy)
├── database.py        # Database connection/setup
├── collectors/
│   ├── listening_history.py
│   ├── user_actions.py
│   └── context_data.py
└── processors/
    ├── aggregators.py
    ├── analyzers.py
    └── exporters.py
```

### 3. Enhanced Player (`ytm_cli/player.py` - Extended)

```python
class EnhancedPlayer:
    def __init__(self):
        self.ai_engine = AIEngine()
        self.data_collector = DataCollector()
        self.recommendation_engine = RecommendationEngine()

    def play_with_ai_enhancements(self, song):
        # Collect listening data
        # Update AI models
        # Prepare next recommendations
        # Handle intelligent queue management
```

### 4. Analytics Engine (`ytm_cli/analytics/`)

```
analytics/
├── __init__.py
├── collectors.py      # Data collection
├── analyzers.py       # Pattern analysis
├── insights.py        # Generate insights
└── visualizers.py     # Data visualization (CLI-friendly)
```

## Data Flow

### 1. User Interaction Flow

```
User Action → Data Collection → AI Processing → Enhanced Response
     ↓              ↓                ↓              ↓
CLI Input → Store in DB → AI Analysis → Smart Recommendations
```

### 2. Recommendation Pipeline

```
User History → AI Model → YTMusic Query → Filter Results → Present to User
     ↓             ↓           ↓             ↓              ↓
Pattern Analysis → Prompts → API Calls → Quality Check → UI Display
```

### 3. Learning Feedback Loop

```
User Feedback → Model Update → Improved Recommendations → Better User Experience
     ↑                                                           ↓
User Actions ← Enhanced Features ← Personalized Content ← AI Learning
```

## Database Schema

### Core Tables

```sql
-- User listening history
CREATE TABLE listening_history (
    id INTEGER PRIMARY KEY,
    video_id TEXT,
    title TEXT,
    artist TEXT,
    timestamp DATETIME,
    duration INTEGER,
    completion_rate REAL,
    source TEXT  -- search, radio, playlist, recommendation
);

-- User actions
CREATE TABLE user_actions (
    id INTEGER PRIMARY KEY,
    video_id TEXT,
    action TEXT,  -- like, dislike, skip, replay, add_to_playlist
    timestamp DATETIME,
    context TEXT  -- what was playing, user's mood, etc.
);

-- AI generated insights
CREATE TABLE ai_insights (
    id INTEGER PRIMARY KEY,
    insight_type TEXT,
    content TEXT,
    confidence REAL,
    timestamp DATETIME,
    metadata JSON
);

-- Context data
CREATE TABLE context_data (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    time_of_day TEXT,
    day_of_week INTEGER,
    weather TEXT,
    user_activity TEXT
);
```

## AI Model Integration

### Model Selection Strategy

```python
class AIModelManager:
    def select_model(self, task_type, context):
        """Dynamically select best AI model for specific tasks"""
        if task_type == "recommendation":
            return self.claude_client  # Best for complex reasoning
        elif task_type == "mood_detection":
            return self.gemini_client  # Fast pattern recognition
        elif task_type == "nlp_search":
            return self.openai_client  # Strong language understanding
```

### Prompt Engineering

```python
RECOMMENDATION_PROMPT = """
Based on the user's listening history and current context:
- Recent plays: {recent_songs}
- Liked genres: {preferred_genres}
- Current mood: {detected_mood}
- Time of day: {time_context}

Recommend 5 songs that would fit perfectly. Explain your reasoning.
"""
```

## Performance Considerations

### Caching Strategy

- **AI Responses**: Cache similar requests for 24 hours
- **User Patterns**: Update pattern cache every 100 songs
- **Recommendations**: Pre-generate during idle time

### Background Processing

- **Data Collection**: Async collection during playback
- **AI Processing**: Background analysis of user patterns
- **Model Updates**: Periodic fine-tuning of local models

### Fallback Mechanisms

- **AI API Failure**: Fall back to rule-based recommendations
- **Network Issues**: Use cached recommendations
- **Model Errors**: Graceful degradation to Phase 1 functionality

## Security & Privacy

### Data Protection

- Local-first approach where possible
- Encrypted storage of sensitive user data
- Anonymized data for AI training
- User control over data sharing

### API Security

- Secure API key management
- Rate limiting for AI API calls
- Error handling for API failures
- Cost monitoring for AI usage

## Configuration System

### Enhanced config.ini

```ini
[ai]
primary_model = claude
fallback_model = local
enable_voice_control = true
cache_duration = 24
max_api_calls_per_day = 1000

[data_collection]
enable_listening_history = true
enable_context_collection = true
enable_mood_detection = true
privacy_level = medium

[recommendations]
exploration_factor = 0.3
mood_weight = 0.4
time_weight = 0.2
history_weight = 0.4
```

This architecture maintains the app's simplicity while adding powerful AI capabilities that enhance rather than complicate the user experience.
