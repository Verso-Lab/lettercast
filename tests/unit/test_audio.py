import pytest
from unittest.mock import Mock, patch
import os
from src.core.audio import transform_audio
from pydub import AudioSegment

@pytest.fixture
def mock_audio_segment():
    with patch('src.core.audio.AudioSegment') as mock:
        mock_audio = Mock()
        mock_audio.channels = 2
        mock_audio.frame_rate = 44100
        mock_audio.set_channels.return_value = mock_audio
        mock_audio.set_frame_rate.return_value = mock_audio
        mock_audio.export.return_value = None
        mock.from_file.return_value = mock_audio
        yield mock

@pytest.fixture
def mock_tempfile():
    with patch('src.core.audio.tempfile.NamedTemporaryFile') as mock:
        mock_file = Mock()
        mock_file.name = '/tmp/test_output.mp3'
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_file)
        mock_context.__exit__ = Mock(return_value=None)
        mock.return_value = mock_context
        yield mock

@pytest.fixture
def temp_audio_file(tmp_path):
    """Create a temporary file that simulates an audio file"""
    audio_path = tmp_path / "test.mp3"
    audio_path.write_bytes(b"fake audio data" * 1000)  # Make file size non-zero
    return str(audio_path)

def test_transform_audio_file_not_found():
    """Test transform_audio with non-existent file"""
    with pytest.raises(FileNotFoundError):
        transform_audio("nonexistent.mp3")

def test_transform_audio_success(mock_audio_segment, mock_tempfile, temp_audio_file):
    """Test successful audio transformation"""
    with patch('os.path.getsize', return_value=1024):  # Mock file size
        result = transform_audio(temp_audio_file)
        
        # Verify mock calls
        mock_audio = mock_audio_segment.from_file.return_value
        mock_audio.set_channels.assert_called_once_with(1)
        mock_audio.set_frame_rate.assert_called_once_with(16000)
        mock_audio.export.assert_called_once()
        
        assert result == '/tmp/test_output.mp3'

def test_transform_audio_processing_error(mock_audio_segment, mock_tempfile, temp_audio_file):
    """Test error handling during audio processing"""
    mock_audio = mock_audio_segment.from_file.return_value
    mock_audio.set_channels.side_effect = Exception("Processing error")
    
    with pytest.raises(Exception, match="Failed to process audio"):
        transform_audio(temp_audio_file) 