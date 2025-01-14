import pytest
from unittest.mock import Mock, patch
from core import PodcastAnalyzer

@pytest.fixture
def mock_genai():
    with patch('google.generativeai') as mock:
        yield mock

@pytest.fixture
def analyzer(mock_genai):
    return PodcastAnalyzer('fake-api-key')

def test_analyzer_initialization(mock_genai):
    """Test analyzer initialization with API key"""
    analyzer = PodcastAnalyzer('test-key')
    mock_genai.configure.assert_called_once_with(api_key='test-key')
    assert analyzer.model is not None

def test_analyzer_initialization_no_key():
    """Test analyzer initialization fails without API key"""
    with pytest.raises(ValueError, match="GEMINI_API_KEY not provided"):
        PodcastAnalyzer(None)

def test_analyze_audio_detailed(analyzer, mock_genai):
    """Test audio analysis with mock response"""
    mock_response = Mock()
    mock_response.text = "Test analysis"
    analyzer.model.generate_content.return_value = mock_response
    
    result = analyzer.analyze_audio_detailed("test.mp3")
    assert result == "Test analysis"
    analyzer.model.generate_content.assert_called_once()

def test_generate_cohesive_newsletter(analyzer, mock_genai):
    """Test newsletter generation with mock response"""
    mock_response = Mock()
    mock_response.text = "Test newsletter"
    analyzer.model.generate_content.return_value = mock_response
    
    analyses = {"test.mp3": "Test analysis"}
    result = analyzer.generate_cohesive_newsletter(analyses)
    assert result == "Test newsletter"
    analyzer.model.generate_content.assert_called_once() 