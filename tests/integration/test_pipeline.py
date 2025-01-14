import pytest
import os
from unittest.mock import Mock, patch
from core import PodcastAnalyzer, transform_audio, format_newsletter, save_newsletter

@pytest.fixture
def mock_genai():
    with patch('google.generativeai') as mock:
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
        mock.GenerativeModel.return_value.generate_content.return_value = mock_response
        yield mock

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

def test_full_pipeline(mock_genai, mock_audio_segment, temp_audio_file, tmp_path):
    """Test the full pipeline from audio to newsletter"""
    # Initialize analyzer
    analyzer = PodcastAnalyzer('test-key')
    
    try:
        # Transform audio
        transformed_audio = transform_audio(temp_audio_file)
        assert os.path.exists(transformed_audio)
        
        # Analyze audio
        analysis = analyzer.analyze_audio_detailed(transformed_audio)
        assert "Test summary" in analysis
        
        # Create newsletter
        analyses = {os.path.basename(temp_audio_file): analysis}
        newsletter = format_newsletter(analyses)
        assert "Test summary" in newsletter
        
        # Save newsletter
        output_path = tmp_path / "test_newsletter.md"
        saved_path = save_newsletter(newsletter, str(output_path))
        assert os.path.exists(saved_path)
        
        # Verify final output
        with open(saved_path) as f:
            content = f.read()
            assert "Test summary" in content
            assert "Test quote" in content
    
    finally:
        # Cleanup
        if os.path.exists(transformed_audio):
            os.unlink(transformed_audio) 