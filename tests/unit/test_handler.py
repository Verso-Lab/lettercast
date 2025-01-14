import pytest
import json
from unittest.mock import patch, Mock
from src.handler import lambda_handler

@pytest.fixture
def mock_transform_audio():
    with patch('src.handler.transform_audio') as mock:
        mock.return_value = '/tmp/transformed.mp3'
        yield mock

@pytest.fixture
def mock_analyzer():
    with patch('src.handler.PodcastAnalyzer') as mock:
        instance = mock.return_value
        instance.analyze_audio_detailed.return_value = "Test analysis"
        yield instance

@pytest.fixture
def mock_format_newsletter():
    with patch('src.handler.format_newsletter') as mock:
        mock.return_value = "Test newsletter"
        yield mock

def test_handler_missing_url():
    """Test handler fails when audio_url is missing"""
    response = lambda_handler({}, None)
    assert response['statusCode'] == 500
    assert 'audio_url not provided' in json.loads(response['body'])['error']

def test_handler_success(mock_transform_audio, mock_analyzer, mock_format_newsletter):
    """Test successful execution of handler"""
    event = {'audio_url': 'https://example.com/podcast.mp3'}
    
    response = lambda_handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['newsletter'] == "Test newsletter"
    
    # Verify function calls
    mock_transform_audio.assert_called_once_with(event['audio_url'])
    mock_analyzer.analyze_audio_detailed.assert_called_once_with('/tmp/transformed.mp3')
    mock_format_newsletter.assert_called_once() 