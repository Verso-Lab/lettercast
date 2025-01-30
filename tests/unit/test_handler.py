import pytest
import json
import os
from unittest.mock import patch, Mock
from src.handler import lambda_handler, process_episode, load_podcasts
from src.core.scraper import Podcast
import pandas as pd

@pytest.fixture
def mock_download_audio():
    with patch('src.handler.download_audio') as mock:
        mock.return_value = '/tmp/downloaded.mp3'
        yield mock

@pytest.fixture
def mock_transform_audio():
    with patch('src.handler.transform_audio') as mock:
        mock.return_value = '/tmp/transformed.mp3'
        yield mock

@pytest.fixture
def mock_analyzer():
    with patch('src.handler.PodcastAnalyzer') as mock:
        instance = mock.return_value
        instance.process_podcast.return_value = '/tmp/podcast_brief_test.md'
        yield instance

@pytest.fixture
def mock_open(tmp_path):
    test_newsletter = "Test newsletter content"
    newsletter_path = tmp_path / "podcast_brief_test.md"
    newsletter_path.write_text(test_newsletter)
    
    with patch('builtins.open', create=True) as mock:
        mock.return_value.__enter__.return_value.read.return_value = test_newsletter
        yield mock

@pytest.fixture
def mock_env():
    with patch.dict('os.environ', {'GEMINI_API_KEY': 'test-key'}):
        yield

@pytest.fixture
def mock_podcasts():
    return [
        Podcast(
            id="1",
            podcast_name="Test Podcast",
            rss_url="https://test.com/feed.xml",
            publisher="Test Publisher"
        )
    ]

@pytest.fixture
def mock_episodes():
    return {
        "episodes": [
            {
                "id": "ep1",
                "episode_name": "Test Episode",
                "url": "https://test.com/episode1.mp3",
                "publish_date": "2024-01-01T00:00:00Z"
            }
        ]
    }

@pytest.fixture
def mock_load_podcasts(mock_podcasts):
    with patch('src.handler.load_podcasts') as mock:
        mock.return_value = mock_podcasts
        yield mock

@pytest.fixture
def mock_get_episodes(mock_episodes):
    with patch('src.handler.get_recent_episodes') as mock:
        mock.return_value = mock_episodes
        yield mock

@pytest.fixture
def mock_makedirs():
    with patch('os.makedirs') as mock:
        yield mock

def test_load_podcasts():
    """Test loading podcasts from CSV"""
    with patch('pandas.read_csv') as mock_csv:
        mock_csv.return_value = pd.DataFrame({
            'id': ['1'],
            'name': ['Test Podcast'],
            'rss_url': ['https://test.com/feed.xml'],
            'publisher': ['Test Publisher'],
            'description': [None],
            'image_url': [None],
            'frequency': [None],
            'tags': [None]
        })
        
        podcasts = load_podcasts()
        assert len(podcasts) == 1
        assert podcasts[0].id == '1'
        assert podcasts[0].podcast_name == 'Test Podcast'

def test_process_episode_success(
    mock_env, mock_download_audio, mock_transform_audio, 
    mock_analyzer, mock_open, mock_makedirs, mock_podcasts
):
    """Test successful processing of a single episode"""
    podcast = mock_podcasts[0]
    episode = {
        "id": "ep1",
        "episode_name": "Test Episode",
        "url": "https://test.com/episode1.mp3"
    }
    
    result = process_episode(podcast, episode, "test-key")
    
    assert result['status'] == 'success'
    assert result['podcast_id'] == podcast.id
    assert result['episode_id'] == episode['id']
    assert result['episode_name'] == episode['episode_name']
    assert 'newsletter' in result

def test_process_episode_failure(
    mock_env, mock_download_audio, mock_transform_audio, 
    mock_analyzer, mock_open, mock_makedirs, mock_podcasts
):
    """Test handling of episode processing failure"""
    mock_download_audio.side_effect = Exception("Download failed")
    
    podcast = mock_podcasts[0]
    episode = {
        "id": "ep1",
        "episode_name": "Test Episode",
        "url": "https://test.com/episode1.mp3"
    }
    
    result = process_episode(podcast, episode, "test-key")
    
    assert result['status'] == 'error'
    assert 'Download failed' in result['error']

def test_handler_success(
    mock_env, mock_load_podcasts, mock_get_episodes,
    mock_download_audio, mock_transform_audio, 
    mock_analyzer, mock_open, mock_makedirs
):
    """Test successful execution of handler with multiple podcasts"""
    response = lambda_handler({}, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert 'results' in body
    assert len(body['results']) == 1
    assert body['results'][0]['status'] == 'success'

def test_handler_partial_failure(
    mock_env, mock_load_podcasts, mock_get_episodes,
    mock_download_audio, mock_transform_audio, 
    mock_analyzer, mock_open, mock_makedirs
):
    """Test handler continues processing after podcast failure"""
    mock_get_episodes.side_effect = Exception("Feed fetch failed")
    
    response = lambda_handler({}, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert 'results' in body
    assert len(body['results']) == 1
    assert body['results'][0]['status'] == 'error'
    assert 'Feed fetch failed' in body['results'][0]['error']

def test_handler_cleanup(
    mock_env, mock_load_podcasts, mock_get_episodes,
    mock_download_audio, mock_transform_audio, 
    mock_analyzer, mock_open, mock_makedirs
):
    """Test cleanup of temporary files during batch processing"""
    with patch('os.path.exists', return_value=True), \
         patch('os.unlink') as mock_unlink:
        
        lambda_handler({}, None)
        
        # Verify temporary files were cleaned up
        assert mock_unlink.call_count >= 2  # At least downloaded and transformed files
        mock_unlink.assert_any_call('/tmp/downloaded.mp3')
        mock_unlink.assert_any_call('/tmp/transformed.mp3') 