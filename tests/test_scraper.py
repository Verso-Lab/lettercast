import pytest
from datetime import datetime
import pytz
from unittest.mock import patch, MagicMock

from src.core.scraper import parse_datetime, RSSParsingError, get_recent_episodes
from src.database.models import Podcast

def test_parse_datetime():
    """Test datetime parsing with various formats"""
    # Test RFC 822 format
    dt = parse_datetime("Wed, 02 Oct 2023 15:00:00 +0000")
    assert isinstance(dt, datetime)
    assert dt.tzinfo is not None
    
    # Test ISO 8601 format
    dt = parse_datetime("2023-10-02T15:00:00Z")
    assert isinstance(dt, datetime)
    assert dt.tzinfo is not None
    
    # Test timezone conversion
    dt = parse_datetime("Wed, 02 Oct 2023 15:00:00 +0200")
    dt_utc = dt.astimezone(pytz.UTC)
    assert dt_utc.hour == 13  # 15:00 +0200 should be 13:00 UTC
    
    # Test invalid format falls back to current time
    dt = parse_datetime("invalid date format")
    assert isinstance(dt, datetime)
    assert dt.tzinfo is not None

@pytest.fixture
def mock_rss_feed():
    """Fixture providing a mock RSS feed with test data"""
    return """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>Test Podcast</title>
            <link>http://example.com</link>
            <description>Test Description</description>
            <item>
                <title>Test Episode</title>
                <guid>test-guid-1</guid>
                <pubDate>Tue, 04 Feb 2025 05:00:00 GMT</pubDate>
                <enclosure url="http://example.com/test.mp3" type="audio/mpeg" length="1024"/>
            </item>
        </channel>
    </rss>
    """

def test_get_recent_episodes(mock_rss_feed):
    """Test episode extraction from RSS feed"""
    # Create test podcast
    podcast = Podcast(
        id="test-id",
        name="Test Podcast",
        rss_url="http://example.com/feed.xml",
        publisher="Test Publisher",
        description="Test Description",
        image_url="http://example.com/image.jpg",
        frequency="weekly",
        tags=["test"]
    )
    
    with patch('requests.get') as mock_get:
        # Mock successful response
        mock_response = MagicMock()
        mock_response.content = mock_rss_feed.encode('utf-8')  # Convert to bytes
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = get_recent_episodes(podcast)
        
        assert isinstance(result, dict)
        assert 'episodes' in result
        assert len(result['episodes']) > 0
        
        episode = result['episodes'][0]
        assert episode['title'] == 'Test Episode'
        assert episode['rss_guid'] == 'test-guid-1'
        assert isinstance(episode['publish_date'], datetime)
        assert episode['url'] == 'http://example.com/test.mp3'
        assert episode['id'] is not None
        assert episode['podcast_id'] == 'test-id'
        assert episode['name'] == 'Test Podcast'

def test_get_recent_episodes_network_error():
    """Test RSS fetching with network errors"""
    podcast = Podcast(
        id="test-id",
        name="Test Podcast",
        rss_url="http://example.com/feed.xml",
        publisher="Test Publisher",
        description="Test Description",
        image_url="http://example.com/image.jpg",
        frequency="weekly",
        tags=["test"]
    )
    
    with patch('requests.get') as mock_get:
        # Mock network error
        mock_get.side_effect = RSSParsingError("Network error")
        
        with pytest.raises(RSSParsingError):
            get_recent_episodes(podcast)

def test_get_recent_episodes_invalid_feed():
    """Test RSS parsing with invalid feed content"""
    podcast = Podcast(
        id="test-id",
        name="Test Podcast",
        rss_url="http://example.com/feed.xml",
        publisher="Test Publisher",
        description="Test Description",
        image_url="http://example.com/image.jpg",
        frequency="weekly",
        tags=["test"]
    )
    
    with patch('requests.get') as mock_get:
        # Mock invalid XML response
        mock_response = MagicMock()
        mock_response.content = b"Invalid XML content"  # Use bytes
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        with pytest.raises(RSSParsingError):
            get_recent_episodes(podcast) 