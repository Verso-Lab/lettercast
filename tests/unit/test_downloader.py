import pytest
import os
import tempfile
import time
from unittest.mock import Mock, patch
from core.downloader import download_audio, MAX_FILE_SIZE_MB, MAX_DOWNLOAD_SECONDS

@pytest.fixture
def mock_response():
    mock = Mock()
    mock.headers = {'content-length': '1024'}
    mock.iter_content.return_value = [b'chunk1', b'chunk2']
    mock.raise_for_status = Mock()
    return mock

@pytest.fixture
def mock_head_response():
    mock = Mock()
    mock.headers = {'content-length': str(1024 * 1024)}  # 1MB
    return mock

def test_invalid_url():
    """Test download fails with invalid URL"""
    with pytest.raises(ValueError, match="Invalid URL"):
        download_audio("not-a-url")

@patch('core.downloader.requests.head')
@patch('core.downloader.requests.get')
def test_file_too_large(mock_get, mock_head):
    """Test download fails when file exceeds Lambda size limit"""
    # Mock a file larger than MAX_FILE_SIZE_MB
    mock_response = Mock()
    mock_response.headers = {
        'content-length': str(int(MAX_FILE_SIZE_MB * 1024 * 1024 * 1.1))  # 10% over limit
    }
    mock_head.return_value = mock_response
    
    with pytest.raises(ValueError, match="exceeds Lambda limit"):
        download_audio("https://example.com/large.mp3")
    
    # Verify we didn't try to download
    mock_get.assert_not_called()

@patch('core.downloader.requests.head')
@patch('core.downloader.requests.get')
@patch('time.time')
def test_download_timeout(mock_time, mock_get, mock_head):
    """Test download fails when it exceeds Lambda timeout"""
    # Mock time to simulate timeout
    start_time = 1000
    mock_time.side_effect = [
        start_time,  # Initial call
        start_time + MAX_DOWNLOAD_SECONDS + 1  # Second call during download
    ]
    
    # Setup responses
    head_response = Mock()
    head_response.headers = {'content-length': '1024'}
    mock_head.return_value = head_response
    
    get_response = Mock()
    get_response.headers = {'content-length': '1024'}
    get_response.iter_content.return_value = [b'chunk']  # Single chunk to trigger timeout
    get_response.raise_for_status = Mock()
    mock_get.return_value = get_response
    
    with pytest.raises(TimeoutError, match="exceeded.*timeout limit"):
        download_audio("https://example.com/podcast.mp3")

@patch('core.downloader.requests.head')
@patch('core.downloader.requests.get')
def test_download_success(mock_get, mock_head):
    """Test successful download"""
    # Setup responses
    head_response = Mock()
    head_response.headers = {'content-length': str(1024 * 1024)}  # 1MB
    mock_head.return_value = head_response
    
    get_response = Mock()
    get_response.headers = {'content-length': str(1024 * 1024)}
    get_response.iter_content.return_value = [b'chunk1', b'chunk2']
    get_response.raise_for_status = Mock()
    mock_get.return_value = get_response
    
    url = "https://example.com/podcast.mp3"
    result = download_audio(url)
    
    try:
        # Verify file exists and has content
        assert os.path.exists(result)
        assert os.path.getsize(result) > 0
        assert result.endswith('.mp3')
        assert result.startswith('/tmp/')  # Verify using Lambda temp directory
        
        # Verify request was made correctly
        mock_get.assert_called_once_with(url, stream=True)
        get_response.iter_content.assert_called_once()
        
    finally:
        # Cleanup
        if os.path.exists(result):
            os.unlink(result)

@patch('core.downloader.requests.head')
@patch('core.downloader.requests.get')
def test_download_cleanup_on_error(mock_get, mock_head):
    """Test temporary file cleanup on error"""
    # Setup responses
    head_response = Mock()
    head_response.headers = {'content-length': str(1024 * 1024)}
    mock_head.return_value = head_response
    
    get_response = Mock()
    get_response.headers = {'content-length': str(1024 * 1024)}
    get_response.iter_content.side_effect = Exception("Write failed")
    get_response.raise_for_status = Mock()
    mock_get.return_value = get_response
    
    with pytest.raises(Exception):
        result = download_audio("https://example.com/podcast.mp3")
        assert not os.path.exists(result)  # File should be cleaned up

def test_download_extension_handling():
    """Test handling of different file extensions"""
    urls = [
        ("https://example.com/podcast.mp3", ".mp3"),
        ("https://example.com/audio.m4a", ".m4a"),
        ("https://example.com/file", ".mp3"),  # Default extension
    ]
    
    with patch('core.downloader.requests.head') as mock_head:
        head_response = Mock()
        head_response.headers = {'content-length': str(1024 * 1024)}
        mock_head.return_value = head_response
        
        with patch('core.downloader.requests.get') as mock_get:
            get_response = Mock()
            get_response.headers = {'content-length': str(1024 * 1024)}
            get_response.iter_content.return_value = [b'chunk1', b'chunk2']
            get_response.raise_for_status = Mock()
            mock_get.return_value = get_response
            
            for url, expected_ext in urls:
                result = download_audio(url)
                try:
                    assert result.endswith(expected_ext)
                    assert result.startswith('/tmp/')
                finally:
                    if os.path.exists(result):
                        os.unlink(result)