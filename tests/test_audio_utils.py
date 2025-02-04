import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock

from src.utils.audio_transformer import transform_audio, AudioTransformationError
from src.utils.downloader import download_audio, DownloadError, FileSizeError

def test_transform_audio_basic(mock_audio_file):
    """Test basic audio transformation functionality"""
    # Test with default parameters
    result_path = transform_audio(mock_audio_file)
    assert os.path.exists(result_path)
    assert os.path.getsize(result_path) > 0
    
    # Cleanup
    os.unlink(result_path)

def test_transform_audio_invalid_input():
    """Test audio transformation with invalid inputs"""
    # Test with non-existent file
    with pytest.raises(AudioTransformationError):
        transform_audio("/nonexistent/audio.mp3")
    
    # Test with empty path
    with pytest.raises(AudioTransformationError):
        transform_audio("")
    
    # Test with None
    with pytest.raises(AudioTransformationError):
        transform_audio(None)

def test_transform_audio_custom_params(mock_audio_file):
    """Test audio transformation with custom parameters"""
    custom_params = {
        'channels': 2,
        'frame_rate': 44100,
        'format': 'wav',
        'quality': '0'
    }
    
    result_path = transform_audio(mock_audio_file, custom_params)
    assert os.path.exists(result_path)
    assert os.path.getsize(result_path) > 0
    
    # Cleanup
    os.unlink(result_path)

@patch('requests.get')
def test_download_audio_success(mock_get):
    """Test successful audio download"""
    # Mock successful response
    mock_response = MagicMock()
    mock_response.headers = {'content-length': '1024'}
    mock_response.iter_content.return_value = [b"test" * 256]  # 1KB of data
    mock_get.return_value = mock_response
    
    url = "http://example.com/test.mp3"
    result = download_audio(url)
    
    assert os.path.exists(result)
    assert os.path.getsize(result) > 0
    
    # Cleanup
    os.unlink(result)

@patch('requests.head')
@patch('requests.get')
def test_download_audio_size_limit(mock_get, mock_head):
    """Test download with file size exceeding limit"""
    # Mock head response with large file size
    mock_head_response = MagicMock()
    mock_head_response.headers = {'content-length': str(500 * 1024 * 1024)}  # 500MB
    mock_head.return_value = mock_head_response
    
    # Mock get response (shouldn't be called)
    mock_get.return_value = MagicMock()
    
    with pytest.raises(FileSizeError):
        download_audio("http://example.com/large.mp3")

@patch('requests.get')
def test_download_audio_network_error(mock_get):
    """Test download with network errors"""
    # Mock network error
    mock_get.side_effect = Exception("Network error")
    
    with pytest.raises(DownloadError):
        download_audio("http://example.com/test.mp3")

def test_download_audio_invalid_url():
    """Test download with invalid URL"""
    with pytest.raises(DownloadError):
        download_audio("not-a-url")
    
    with pytest.raises(DownloadError):
        download_audio("")
    
    with pytest.raises(DownloadError):
        download_audio(None) 