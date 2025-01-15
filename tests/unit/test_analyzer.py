import pytest
import os
from datetime import datetime
from unittest.mock import Mock, patch
from core import PodcastAnalyzer, AnalyzerError, InvalidAnalysisError

@pytest.fixture
def mock_genai():
    with patch('core.analyzer.genai') as mock:
        mock_model = Mock()
        mock.GenerativeModel.return_value = mock_model
        yield mock

@pytest.fixture
def analyzer(mock_genai):
    analyzer = PodcastAnalyzer('fake-api-key')
    # Mock the generate_content method after analyzer creation
    mock_response = Mock()
    analyzer.model.generate_content = Mock(return_value=mock_response)
    return analyzer

@pytest.fixture
def sample_analysis():
    return """
TLDR: Test summary

WHY NOW: Test context

KEY POINTS:
→ Point 1
→ Point 2
→ Point 3

QUOTED: "Test quote" —Speaker
"""

@pytest.fixture
def invalid_analysis():
    return """
TLDR: Test summary

KEY POINTS:
→ Point 1
"""

def test_analyzer_initialization():
    """Test analyzer initialization with API key"""
    with patch('core.analyzer.genai') as mock_genai:
        analyzer = PodcastAnalyzer('test-key')
        mock_genai.configure.assert_called_once_with(api_key='test-key')
        assert analyzer.model is not None

def test_analyzer_initialization_no_key():
    """Test analyzer initialization fails without API key"""
    with pytest.raises(ValueError, match="GEMINI_API_KEY not provided"):
        PodcastAnalyzer(None)

def test_validate_analysis(analyzer, sample_analysis):
    """Test analysis validation with valid content"""
    analyzer.validate_analysis(sample_analysis)  # Should not raise

def test_validate_analysis_invalid(analyzer, invalid_analysis):
    """Test analysis validation with missing sections"""
    with pytest.raises(InvalidAnalysisError) as exc:
        analyzer.validate_analysis(invalid_analysis)
    assert "missing required sections" in str(exc.value)
    assert "WHY NOW:" in str(exc.value)
    assert "QUOTED:" in str(exc.value)

@patch('pathlib.Path.read_bytes')
def test_analyze_audio_detailed(mock_read_bytes, analyzer, mock_genai, sample_analysis):
    """Test audio analysis with mock response"""
    # Mock file reading
    mock_read_bytes.return_value = b'fake audio data'
    
    # Set up mock response
    analyzer.model.generate_content.return_value.text = sample_analysis
    
    result = analyzer.analyze_audio_detailed("test.mp3")
    assert result == sample_analysis
    analyzer.model.generate_content.assert_called_once()
    mock_read_bytes.assert_called_once()

@patch('pathlib.Path.read_bytes')
def test_analyze_audio_invalid_response(mock_read_bytes, analyzer, mock_genai, invalid_analysis):
    """Test audio analysis with invalid response"""
    # Mock file reading
    mock_read_bytes.return_value = b'fake audio data'
    
    # Set up mock response
    analyzer.model.generate_content.return_value.text = invalid_analysis
    
    with pytest.raises(InvalidAnalysisError):
        analyzer.analyze_audio_detailed("test.mp3")
    
    mock_read_bytes.assert_called_once()

def test_format_newsletter(analyzer, sample_analysis):
    """Test newsletter formatting with valid analysis"""
    result = analyzer.format_newsletter(sample_analysis)
    
    # Check basic structure
    assert "# Lettercast" in result
    assert datetime.now().strftime("%B %d, %Y") in result
    
    # Check formatting
    assert "**KEY POINTS:**" in result
    assert "**TLDR:**" in result
    assert "**WHY NOW:**" in result
    assert "**QUOTED:**" in result
    
    # Check content and formatting
    assert "Test summary" in result
    assert "Test quote" in result
    assert "• Point 1" in result  # Check bullet point conversion
    assert "• Point 2" in result

def test_format_newsletter_with_title(analyzer, sample_analysis):
    """Test newsletter formatting with podcast title"""
    title = "Test Podcast"
    result = analyzer.format_newsletter(sample_analysis, title)
    
    assert "# Lettercast" in result
    assert f"## {title}" in result
    assert "Test summary" in result
    assert "• Point 1" in result  # Check bullet point conversion

def test_format_newsletter_invalid(analyzer, invalid_analysis):
    """Test newsletter formatting with invalid analysis"""
    with pytest.raises(InvalidAnalysisError):
        analyzer.format_newsletter(invalid_analysis)

def test_save_newsletter(analyzer, tmp_path):
    """Test newsletter saving with custom path"""
    test_content = "Test newsletter content"
    output_path = tmp_path / "test_newsletter.md"
    
    result = analyzer.save_newsletter(test_content, str(output_path))
    
    assert result == str(output_path)
    assert output_path.exists()
    assert output_path.read_text() == test_content

def test_save_newsletter_default_path(analyzer):
    """Test newsletter saving with default path"""
    test_content = "Test newsletter content"
    expected_filename = f"lettercast_{datetime.now().strftime('%Y%m%d')}.md"
    result = None
    
    try:
        result = analyzer.save_newsletter(test_content)
        
        assert os.path.basename(result) == expected_filename
        assert os.path.exists(result)
        with open(result) as f:
            assert f.read() == test_content
            
    finally:
        # Cleanup
        if result and os.path.exists(result):
            os.unlink(result)

def test_save_newsletter_error(analyzer, tmp_path):
    """Test newsletter saving with write error"""
    test_content = "Test newsletter content"
    output_path = tmp_path / "nonexistent" / "test.md"
    
    with pytest.raises(AnalyzerError) as exc:
        analyzer.save_newsletter(test_content, str(output_path))
    assert "Failed to save newsletter" in str(exc.value)

@patch('pathlib.Path.read_bytes')
def test_process_podcast(mock_read_bytes, analyzer, mock_genai, sample_analysis, tmp_path):
    """Test full podcast processing pipeline"""
    # Mock file reading
    mock_read_bytes.return_value = b'fake audio data'
    
    # Set up mock response
    analyzer.model.generate_content.return_value.text = sample_analysis
    
    # Process podcast
    output_path = tmp_path / "test_newsletter.md"
    result = analyzer.process_podcast(
        "test.mp3",
        title="Test Podcast",
        output_path=str(output_path)
    )
    
    # Verify result
    assert result == str(output_path)
    assert output_path.exists()
    
    # Check content
    content = output_path.read_text()
    assert "Test Podcast" in content
    assert "Test summary" in content
    assert "Test quote" in content
    
    # Verify mocks
    mock_read_bytes.assert_called_once() 