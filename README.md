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

### CLI mode
Process podcasts using the main CLI interface:
```bash
poetry run python src/cli.py
```
When prompted, you can:
- Enter a podcast URL to analyze
- Press Enter without a URL to use a default test podcast

The script will generate a newsletter summary in the `newsletters/` directory.

### Local audio testing
Test the system with local audio files (for more rapid prompt iteration):
```bash
poetry run python tests/tools/test_prompt.py
```
The script will:
1. Display available audio files from the `audio/` directory
2. Allow selection of an existing file or input of a custom path
3. Generate a newsletter summary in the `newsletters/` directory

## Project structure

```
lettercast/
├── src/
│   ├── core/
│   │   ├── analyzer.py          # Main analysis logic
│   │   ├── audio_transformer.py # Audio processing
│   │   ├── downloader.py        # Podcast downloading
│   │   └── prompts.py           # Analysis prompts
│   ├── utils/
│   │   └── logging_config.py    # Structured logging
│   ├── cli.py                   # CLI entry point
│   └── handler.py               # Lambda handler
├── tests/
│   ├── tools/                   # Testing utilities and scripts
│   ├── unit/                    # Unit tests
│   ├── integration/             # Integration tests
│   └── conftest.py              # Test configuration
└── newsletters/                 # Generated analyses
```

## Development

### Logging setup
```python
import logging
from utils.logging_config import setup_logging

logger = logging.getLogger(__name__)
setup_logging()
```

### Known issues
- gRPC shutdown warning can be safely ignored: `grpc_wait_for_shutdown_with_timeout() timed out`

## Troubleshooting

- FFmpeg not found: Run `brew install ffmpeg`
- API errors: Verify Gemini API key and quota
- Memory issues: Check audio file size and compression settings