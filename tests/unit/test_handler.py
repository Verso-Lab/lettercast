import pytest
import json
import os
from unittest.mock import patch, Mock
from src.handler import lambda_handler

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

def test_handler_missing_url(mock_env):
    """Test handler fails when audio_url is missing"""
    with pytest.raises(ValueError, match="audio_url not provided"):
        lambda_handler({}, None)

def test_handler_success(mock_env, mock_download_audio, mock_transform_audio, mock_analyzer, mock_open):
    """Test successful execution of handler"""
    event = {'audio_url': 'https://example.com/podcast.mp3'}
    
    response = lambda_handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['newsletter'] == "Test newsletter content"
    assert body['file_path'] == '/tmp/podcast_brief_test.md'
    
    # Verify function calls
    mock_download_audio.assert_called_once_with(event['audio_url'])
    mock_transform_audio.assert_called_once_with('/tmp/downloaded.mp3')
    mock_analyzer.process_podcast.assert_called_once_with(
        '/tmp/transformed.mp3',
        title='podcast.mp3',
        output_path='newsletters/lettercast_podcast.md'
    )

@patch('os.unlink')
@patch('os.path.exists', return_value=True)
def test_handler_cleanup(mock_exists, mock_unlink, mock_env, mock_download_audio, mock_transform_audio, mock_analyzer, mock_open):
    """Test cleanup of temporary files"""
    event = {'audio_url': 'https://example.com/podcast.mp3'}
    
    lambda_handler(event, None)
    
    # Verify both temporary files were cleaned up
    assert mock_unlink.call_count == 2
    mock_unlink.assert_any_call('/tmp/downloaded.mp3')
    mock_unlink.assert_any_call('/tmp/transformed.mp3')

def test_handler_download_failure(mock_env, mock_download_audio, mock_transform_audio, mock_analyzer, mock_open):
    """Test handler handles download failures"""
    mock_download_audio.side_effect = Exception("Download failed")
    
    with pytest.raises(Exception, match="Download failed"):
        lambda_handler({'audio_url': 'https://example.com/podcast.mp3'}, None)

def test_handler_lambda_error(mock_env, mock_download_audio, mock_transform_audio, mock_analyzer, mock_open):
    """Test handler returns error response in Lambda context"""
    mock_download_audio.side_effect = Exception("Download failed")
    
    response = lambda_handler({'audio_url': 'https://example.com/podcast.mp3'}, context=Mock())
    
    assert response['statusCode'] == 500
    assert 'Download failed' in json.loads(response['body'])['error'] 