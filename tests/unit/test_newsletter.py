import pytest
import os
from datetime import datetime
from core.newsletter import (
    format_newsletter,
    save_newsletter,
    validate_analysis,
    InvalidAnalysisError,
    NewsletterError
)

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

def test_validate_analysis(sample_analysis):
    """Test analysis validation with valid content"""
    validate_analysis(sample_analysis)  # Should not raise

def test_validate_analysis_invalid(invalid_analysis):
    """Test analysis validation with missing sections"""
    with pytest.raises(InvalidAnalysisError) as exc:
        validate_analysis(invalid_analysis)
    assert "missing required sections" in str(exc.value)
    assert "WHY NOW:" in str(exc.value)
    assert "QUOTED:" in str(exc.value)

def test_format_newsletter(sample_analysis):
    """Test newsletter formatting with valid analysis"""
    result = format_newsletter(sample_analysis)
    
    # Check basic structure
    assert "# Podcast Brief" in result
    assert datetime.now().strftime("%B %d") in result
    
    # Check formatting
    assert "**KEY POINTS:**" in result
    assert "**TLDR:**" in result
    assert "**WHY NOW:**" in result
    assert "**QUOTED:**" in result
    
    # Check content
    assert "Test summary" in result
    assert "Test quote" in result

def test_format_newsletter_with_title(sample_analysis):
    """Test newsletter formatting with podcast title"""
    title = "Test Podcast"
    result = format_newsletter(sample_analysis, title)
    
    assert f"## {title}" in result
    assert "Test summary" in result

def test_format_newsletter_invalid(invalid_analysis):
    """Test newsletter formatting with invalid analysis"""
    with pytest.raises(InvalidAnalysisError):
        format_newsletter(invalid_analysis)

def test_save_newsletter(tmp_path):
    """Test newsletter saving with custom path"""
    test_content = "Test newsletter content"
    output_path = tmp_path / "test_newsletter.md"
    
    result = save_newsletter(test_content, str(output_path))
    
    assert result == str(output_path)
    assert output_path.exists()
    assert output_path.read_text() == test_content

def test_save_newsletter_default_path():
    """Test newsletter saving with default path"""
    test_content = "Test newsletter content"
    expected_filename = f"podcast_brief_{datetime.now().strftime('%Y%m%d')}.md"
    
    try:
        result = save_newsletter(test_content)
        
        assert os.path.basename(result) == expected_filename
        assert os.path.exists(result)
        with open(result) as f:
            assert f.read() == test_content
            
    finally:
        # Cleanup
        if os.path.exists(result):
            os.unlink(result)

def test_save_newsletter_error(tmp_path):
    """Test newsletter saving with write error"""
    test_content = "Test newsletter content"
    output_path = tmp_path / "nonexistent" / "test.md"
    
    with pytest.raises(NewsletterError) as exc:
        save_newsletter(test_content, str(output_path))
    assert "Failed to save newsletter" in str(exc.value) 