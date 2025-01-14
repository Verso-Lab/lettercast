import pytest
from unittest.mock import Mock, patch
import os
from core import transform_audio
from pydub import AudioSegment

@pytest.fixture
def mock_audio_segment():
    with patch('core.audio.AudioSegment') as mock:
        mock_audio = Mock()
        mock_audio.channels = 2
        mock_audio.frame_rate = 44100
        mock.from_file.return_value = mock_audio
        yield mock

@pytest.fixture
def temp_audio_file(tmp_path):
    """Create a temporary file that simulates an audio file"""
    audio_path = tmp_path / "test.mp3"
    audio_path.write_bytes(b"fake audio data")
    return str(audio_path)

def test_transform_audio_file_not_found():
    """Test transform_audio with non-existent file"""
    with pytest.raises(FileNotFoundError):
        transform_audio("nonexistent.mp3")

def test_transform_audio_success(mock_audio_segment, temp_audio_file):
    """Test successful audio transformation"""
    result = transform_audio(temp_audio_file)
    
    # Verify file exists and was processed
    assert os.path.exists(result)
    assert os.path.getsize(result) > 0
    
    # Verify audio processing steps were called
    mock_audio = mock_audio_segment.from_file.return_value
    mock_audio.set_channels.assert_called_once_with(1)
    mock_audio.set_frame_rate.assert_called_once_with(16000)
    
    # Cleanup
    os.unlink(result)

def test_transform_audio_processing_error(mock_audio_segment, temp_audio_file):
    """Test error handling during audio processing"""
    mock_audio = mock_audio_segment.from_file.return_value
    mock_audio.set_channels.side_effect = Exception("Processing error")
    
    with pytest.raises(Exception, match="Failed to process audio"):
        transform_audio(temp_audio_file) 