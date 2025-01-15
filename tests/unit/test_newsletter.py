import pytest
import os
from datetime import datetime
from src.core.analyzer import PodcastAnalyzer, InvalidAnalysisError, AnalyzerError

@pytest.fixture
def ensure_newsletters_dir():
    """Ensure the newsletters directory exists"""
    os.makedirs('newsletters', exist_ok=True)
    yield
    # Don't cleanup - other tests might need it

@pytest.fixture
def analyzer():
    return PodcastAnalyzer('test-key')

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

def test_format_newsletter(analyzer, sample_analysis):
    """Test newsletter formatting with valid analysis"""
    result = analyzer.format_newsletter(sample_analysis)
    
    # Check basic structure
    assert "# Lettercast" in result
    assert datetime.now().strftime("%B %d") in result
    
    # Check formatting
    assert "**KEY POINTS:**" in result
    assert "**TLDR:**" in result
    assert "**WHY NOW:**" in result
    assert "**QUOTED:**" in result
    
    # Check content
    assert "Test summary" in result
    assert "Test quote" in result

def test_format_newsletter_with_title(analyzer, sample_analysis):
    """Test newsletter formatting with podcast title"""
    title = "Test Podcast"
    result = analyzer.format_newsletter(sample_analysis, title)
    
    assert f"## {title}" in result
    assert "Test summary" in result

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
    assert os.path.exists(result)
    with open(result) as f:
        assert f.read() == test_content

def test_save_newsletter_default_path(analyzer, ensure_newsletters_dir):
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