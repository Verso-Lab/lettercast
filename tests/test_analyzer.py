import pytest
from datetime import datetime
import pytz
from unittest.mock import patch, MagicMock, AsyncMock

from src.core.analyzer import PodcastAnalyzer, AnalyzerError

@patch('google.generativeai.configure')
@patch('google.generativeai.GenerativeModel')
def test_analyzer_initialization(mock_model, mock_configure, mock_api_key):
    """Test PodcastAnalyzer initialization with valid and invalid API keys"""
    # Mock the model
    mock_instance = MagicMock()
    mock_model.return_value = mock_instance
    
    # Test valid initialization
    analyzer = PodcastAnalyzer(mock_api_key)
    assert analyzer is not None
    assert analyzer.model is not None
    
    # Verify API was configured
    mock_configure.assert_called_once_with(api_key=mock_api_key)
    
    # Test initialization with invalid API key
    with pytest.raises(ValueError):
        PodcastAnalyzer("")
    
    with pytest.raises(ValueError):
        PodcastAnalyzer(None)

@patch('google.generativeai.configure')
@patch('google.generativeai.GenerativeModel')
def test_validate_analysis(mock_model, mock_configure, mock_api_key):
    """Test analysis validation with various content structures"""
    # Mock the model
    mock_instance = MagicMock()
    mock_model.return_value = mock_instance
    
    analyzer = PodcastAnalyzer(mock_api_key)
    
    # Valid analysis with all required sections
    valid_analysis = """
    # TLDR
    Quick summary here.
    
    # The big picture
    Overview here.
    
    # Highlights
    Key points here.
    
    # Quoted
    Important quotes here.
    
    # Worth your time if
    Recommendations here.
    """
    
    # Should not raise an exception
    analyzer.validate_analysis(valid_analysis)
    
    # Test missing sections - should only log warning
    invalid_analysis = """
    # TLDR
    Quick summary here.
    
    # Highlights
    Key points here.
    """
    
    with patch('logging.Logger.warning') as mock_warning:
        analyzer.validate_analysis(invalid_analysis)
        mock_warning.assert_called_once()
        warning_msg = mock_warning.call_args[0][0]
        assert "missing required sections" in warning_msg.lower()
        assert "The big picture" in warning_msg
        assert "Quoted" in warning_msg
        assert "Worth your time if" in warning_msg

@patch('google.generativeai.configure')
@patch('google.generativeai.GenerativeModel')
def test_process_podcast(mock_model, mock_configure, mock_api_key, mock_audio_file):
    """Test podcast processing with mock audio file"""
    # Mock the model's generate_content method
    mock_response = MagicMock()
    mock_response.text = """
    # TLDR
    Test summary
    
    # The big picture
    Test overview
    
    # Highlights
    Test highlights
    
    # Quoted
    Test quotes
    
    # Worth your time if
    Test recommendations
    """
    mock_instance = MagicMock()
    mock_instance.generate_content.return_value = mock_response
    mock_model.return_value = mock_instance
    
    analyzer = PodcastAnalyzer(mock_api_key)
    
    # Test with missing required parameters
    with pytest.raises(AnalyzerError):
        analyzer.process_podcast(
            audio_path="",
            name="Test Podcast",
            title="Test Episode",
            category="interview",
            publish_date=datetime.now(pytz.UTC)
        )
    
    # Test with non-existent audio file
    with pytest.raises(AnalyzerError):
        analyzer.process_podcast(
            audio_path="/nonexistent/path.mp3",
            name="Test Podcast",
            title="Test Episode",
            category="interview",
            publish_date=datetime.now(pytz.UTC)
        )
    
    # Test with valid parameters and mock audio file
    result = analyzer.process_podcast(
        audio_path=mock_audio_file,
        name="Test Podcast",
        title="Test Episode",
        category="interview",
        publish_date=datetime.now(pytz.UTC),
        prompt_addition="Test context",
        episode_description="Test description"
    )
    
    # Verify the result structure
    assert isinstance(result, str)
    assert "TLDR" in result
    assert "The big picture" in result
    assert "Highlights" in result
    assert "Quoted" in result
    assert "Worth your time if" in result
    assert "Test Podcast" in result
    assert "Test Episode" in result 