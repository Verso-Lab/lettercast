import pytest
import os
from unittest.mock import Mock, patch
from src.core import PodcastAnalyzer
from src.core.audio import transform_audio

@pytest.fixture
def mock_genai():
    with patch('src.core.analyzer.genai') as mock:
        mock_response = Mock()
        mock_response.text = """
TLDR: Test summary

WHY NOW: Test context

KEY POINTS:
→ Point 1
→ Point 2
→ Point 3

QUOTED: "Test quote" —Speaker
"""
        # Mock the model and its response
        mock_model = Mock()
        mock_model.generate_content = Mock(return_value=mock_response)
        mock.GenerativeModel = Mock(return_value=mock_model)
        
        yield mock

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
def temp_audio_file(tmp_path):
    """Create a temporary file that simulates an audio file"""
    audio_path = tmp_path / "test.mp3"
    audio_path.write_bytes(b"fake audio data")
    return str(audio_path)

def test_full_pipeline(mock_genai, mock_audio_segment, temp_audio_file, tmp_path):
    """Test the full pipeline from audio to newsletter"""
    analyzer = PodcastAnalyzer('test-key')
    transformed_audio = None
    
    try:
        # Transform audio
        transformed_audio = transform_audio(temp_audio_file)
        assert os.path.exists(transformed_audio)
        
        # Analyze audio and create newsletter
        saved_path = analyzer.process_podcast(
            transformed_audio,
            title=os.path.basename(temp_audio_file),
            output_path=str(tmp_path / "test_newsletter.md")
        )
        
        # Verify final output
        assert os.path.exists(saved_path)
        with open(saved_path) as f:
            content = f.read()
            assert "Test summary" in content
            assert "Test quote" in content
    
    finally:
        # Cleanup
        if transformed_audio and os.path.exists(transformed_audio):
            os.unlink(transformed_audio) 