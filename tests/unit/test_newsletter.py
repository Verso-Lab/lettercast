import pytest
from datetime import datetime
from core import format_newsletter, save_newsletter

@pytest.fixture
def sample_analyses():
    return {
        "test.mp3": """
TLDR: Test summary

WHY NOW: Test context

KEY POINTS:
→ Point 1
→ Point 2
→ Point 3

QUOTED: "Test quote" —Speaker
"""
    }

def test_format_newsletter(sample_analyses):
    """Test newsletter formatting"""
    result = format_newsletter(sample_analyses)
    
    # Check basic structure
    assert "# Podcast Briefing" in result
    assert datetime.now().strftime("%B %d") in result
    
    # Check formatting
    assert "**KEY POINTS:**" in result
    assert "**TLDR:**" in result
    assert "**WHY NOW:**" in result
    assert "**QUOTED:**" in result
    
    # Check content
    assert "test.mp3" in result
    assert "Test summary" in result
    assert "Test quote" in result

def test_format_newsletter_empty():
    """Test newsletter formatting with empty analyses"""
    result = format_newsletter({})
    assert "# Podcast Briefing" in result
    assert "Quick update on today's episodes" in result

def test_save_newsletter(tmp_path):
    """Test newsletter saving"""
    test_content = "Test newsletter content"
    output_path = tmp_path / "test_newsletter.md"
    
    result = save_newsletter(test_content, str(output_path))
    
    assert result == str(output_path)
    assert output_path.exists()
    assert output_path.read_text() == test_content

def test_save_newsletter_default_path():
    """Test newsletter saving with default path"""
    test_content = "Test newsletter content"
    expected_filename = f"podcast_digest_{datetime.now().strftime('%Y%m%d')}.md"
    
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