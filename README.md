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
```bash
echo "GEMINI_API_KEY=your-api-key-here" > .env
```

## Usage

Run the CLI:
```bash
poetry run python src/cli.py
```

You can either:
- Enter a podcast URL when prompted
- Press Enter without a URL to analyze a default test podcast

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
│   ├── handler.py          # Lambda handler
│   └── cli.py              # CLI entry point
└── newsletters/            # Generated analyses
```

## Development Notes

- Logging Setup:
```python
import logging
from utils.logging_config import setup_logging

logger = logging.getLogger(__name__)
setup_logging()
```

- Known Issues:
  - gRPC shutdown warning can be safely ignored: `grpc_wait_for_shutdown_with_timeout() timed out`

## Troubleshooting

- FFmpeg not found: `brew install ffmpeg`
- API errors: Verify Gemini API key and quota
- Memory issues: Check audio file size and compression settings