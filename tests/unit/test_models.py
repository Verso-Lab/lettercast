import pytest
from datetime import datetime, timezone
from uuid import UUID
from src.database.models import Episode, NewlineString

def test_newline_string_type():
    """Test the NewlineString type's encoding/decoding"""
    type_handler = NewlineString()
    
    # Test encoding (saving to DB)
    assert type_handler.process_bind_param("Line 1\nLine 2", None) == "Line 1\\nLine 2"
    assert type_handler.process_bind_param(None, None) is None
    
    # Test decoding (loading from DB)
    assert type_handler.process_result_value("Line 1\\nLine 2", None) == "Line 1\nLine 2"
    assert type_handler.process_result_value(None, None) is None

def test_episode_summary_newlines():
    """Test that newlines are properly handled in Episode summaries"""
    # Create an episode with newlines
    summary_with_newlines = "Line 1\nLine 2\nLine 3"
    episode = Episode(
        rss_guid="test-guid",
        title="Test Episode",
        publish_date=datetime.now(timezone.utc),
        summary=summary_with_newlines
    )
    
    # The summary should be stored as-is in the model
    # The type handler will handle conversion when interacting with the database
    assert episode.summary == summary_with_newlines
    
    # Test setting new summary
    new_summary = "New Line 1\nNew Line 2"
    episode.summary = new_summary
    assert episode.summary == new_summary
    
    # Test None handling
    episode.summary = None
    assert episode.summary is None

def test_episode_summary_database_round_trip():
    """Test that newlines are properly handled when simulating database storage"""
    type_handler = NewlineString()
    
    # Create an episode with newlines
    original_summary = "Line 1\nLine 2\nLine 3"
    episode = Episode(
        rss_guid="test-guid",
        title="Test Episode",
        publish_date=datetime.now(timezone.utc),
        summary=original_summary
    )
    
    # Simulate storing to database by encoding the value
    db_value = type_handler.process_bind_param(episode.summary, None)
    assert db_value == "Line 1\\nLine 2\\nLine 3"
    
    # Simulate loading from database by decoding the value
    loaded_value = type_handler.process_result_value(db_value, None)
    assert loaded_value == original_summary
    
    # Create a new episode instance with the loaded value
    loaded_episode = Episode(
        rss_guid="test-guid",
        title="Test Episode",
        publish_date=datetime.now(timezone.utc),
        summary=loaded_value
    )
    
    # Verify the summary is correct
    assert loaded_episode.summary == original_summary