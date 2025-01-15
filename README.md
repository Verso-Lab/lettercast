# Lettercast

AI-powered podcast analysis system that generates newsletter summaries using Google's Gemini API.

## Requirements

- Python 3.13+
- Poetry
- FFmpeg
- Google Cloud API key (Gemini)

## Setup

1. Install dependencies:
```bash
poetry install
```

2. Configure environment:
Create a `.env` file in the project root:
```
GEMINI_API_KEY=your-api-key-here
```

## Usage

To test, run the analyzer:
```bash
poetry run python src/handler.py
```

## Project Structure

```
lettercast/
├── src/
│   ├── core/
│   │   ├── analyzer.py     # Main analysis logic
│   │   ├── audio.py        # Audio processing
│   │   ├── downloader.py   # Podcast downloading
│   │   └── prompts.py      # Analysis prompts
│   ├── utils/
│   │   └── logging.py      # Structured logging
│   └── handler.py          # Main entry point
└── newsletters/            # Generated analyses
```

## Development Notes

- Use the provided logger:
```python
from utils import get_logger
logger = get_logger(__name__)
```

- Known Issues:
  - gRPC shutdown warning can be safely ignored: `grpc_wait_for_shutdown_with_timeout() timed out`

## Troubleshooting

- FFmpeg not found: `brew install ffmpeg`
- API errors: Verify Gemini API key and quota
- Memory issues: Check audio file size and compression settings