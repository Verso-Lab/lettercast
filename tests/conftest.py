import os
import pytest
import pytest_asyncio
import shutil
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

# Mock Gemini API key for testing
@pytest.fixture
def mock_api_key():
    return "mock_api_key_for_testing"

# Async database fixtures
@pytest_asyncio.fixture
async def test_engine():
    # Use SQLite for testing
    TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True
    )
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture
async def test_async_session(test_engine):
    async_session = sessionmaker(
        test_engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )
    async with async_session() as session:
        yield session

# Mock audio file fixture
@pytest.fixture
def mock_audio_file(tmp_path):
    """Create a test audio file for testing.
    
    This copies a real test MP3 file to a temporary location.
    """
    # Create tests/fixtures directory if it doesn't exist
    fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
    os.makedirs(fixtures_dir, exist_ok=True)
    
    # Path to test MP3 file
    test_mp3 = os.path.join(fixtures_dir, "test.mp3")
    
    # If test file doesn't exist, create a silent MP3
    if not os.path.exists(test_mp3):
        import subprocess
        subprocess.run([
            "ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
            "-t", "1", "-q:a", "9", "-acodec", "libmp3lame", test_mp3
        ], check=True)
    
    # Copy to temporary location
    temp_path = tmp_path / "test_audio.mp3"
    shutil.copy2(test_mp3, temp_path)
    return str(temp_path)

# Mock RSS feed fixture
@pytest.fixture
def mock_rss_feed():
    return """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>Test Podcast</title>
            <link>http://example.com</link>
            <description>Test Description</description>
            <item>
                <title>Test Episode</title>
                <guid>test-guid-1</guid>
                <pubDate>Tue, 01 Jan 2024 12:00:00 +0000</pubDate>
                <enclosure url="http://example.com/test.mp3" type="audio/mpeg" length="1024"/>
            </item>
        </channel>
    </rss>
    """ 