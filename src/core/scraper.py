import logging
import uuid
from datetime import datetime
from typing import Dict, List

import pytz
import requests
from lxml import etree
from database.models import Podcast

logger = logging.getLogger(__name__)

class RSSParsingError(Exception):
    """Raised when RSS feed cannot be parsed"""
    pass

def parse_datetime(date_str: str) -> datetime:
    """Convert RSS date string to UTC datetime"""
    try:
        # Common RSS date formats
        for fmt in [
            '%a, %d %b %Y %H:%M:%S %z',  # RFC 822
            '%a, %d %b %Y %H:%M:%S %Z',  # RFC 822 with timezone name
            '%Y-%m-%dT%H:%M:%S%z',       # ISO 8601
            '%Y-%m-%dT%H:%M:%SZ',        # ISO 8601 UTC
        ]:
            try:
                dt = datetime.strptime(date_str, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=pytz.UTC)
                return dt
            except ValueError:
                continue
        
        # Fallback to dateutil parser
        from dateutil import parser
        dt = parser.parse(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=pytz.UTC)
        return dt
    except Exception as e:
        logger.warning(f"Failed to parse date {date_str}: {e}")
        return datetime.now(pytz.UTC)

def get_recent_episodes(podcast: Podcast, limit: int | None = None) -> Dict:
    """Fetch and parse podcast RSS feed.
    
    Args:
        podcast: Podcast metadata
        limit: Max episodes to return
        
    Returns:
        Dict with episodes and metadata
    """
    if not podcast:
        raise ValueError("Podcast cannot be None")
    if not podcast.rss_url:
        raise ValueError("Podcast RSS URL cannot be empty")
    if not podcast.name:
        raise ValueError("Podcast name cannot be empty")
        
    try:
        logger.info(f"Scraping RSS feed for {podcast.name} from {podcast.rss_url}")
        
        # Fetch and parse RSS
        response = requests.get(podcast.rss_url, timeout=30)
        response.raise_for_status()
        
        try:
            root = etree.fromstring(response.content)
        except etree.XMLSyntaxError as e:
            raise RSSParsingError(f"Invalid XML in RSS feed: {str(e)}")
        
        # RSS namespaces
        namespaces = {
            'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd',
            'content': 'http://purl.org/rss/1.0/modules/content/',
            'atom': 'http://www.w3.org/2005/Atom'
        }
        
        # Validate feed structure
        channel = root.find('channel')
        if channel is None:
            raise RSSParsingError("Invalid RSS feed - no channel element found")
            
        items = channel.findall('item')
        if not items:
            raise RSSParsingError("No episodes found in feed")
        
        # Process episodes
        episodes = []
        items_to_process = items[:limit] if limit is not None else items
        for item in items_to_process:
            try:
                # Get episode identifier
                guid = item.find('guid')
                rss_guid = guid.text if guid is not None else item.findtext('link')
                
                # Parse publish date
                pub_date = item.findtext('pubDate')
                if pub_date:
                    publish_date = parse_datetime(pub_date)
                else:
                    publish_date = datetime.now(pytz.UTC)
                
                # Find audio URL
                audio_url = None
                enclosure = item.find('enclosure')
                if enclosure is not None:
                    audio_url = enclosure.get('url')
                    mime_type = enclosure.get('type', '')
                    if not audio_url or not mime_type.startswith('audio/'):
                        # Try other enclosures for audio
                        for enc in item.findall('enclosure'):
                            if enc.get('type', '').startswith('audio/'):
                                audio_url = enc.get('url')
                                break
                
                if not audio_url:
                    logger.warning(f"No audio URL found for episode: {item.findtext('title', '')}")
                    continue
                
                # Create episode entry
                episode = {
                    'rss_guid': rss_guid,
                    'title': item.findtext('title', '').strip(),
                    'publish_date': publish_date,
                    'url': audio_url,
                }

                # Add description if available
                description = (
                    (item.find('content:encoded', namespaces).text if item.find('content:encoded', namespaces) is not None else None) or 
                    item.findtext('description', '').strip()
                )
                if description:
                    episode['episode_description'] = description

                # Add metadata
                episode.update({
                    'id': str(uuid.uuid4()),
                    'podcast_id': podcast.id,
                    'name': podcast.name,
                })
                
                episodes.append(episode)
                
            except Exception as e:
                logger.error(f"Error processing episode: {e}")
                continue
        
        return {"episodes": episodes}
    
    except requests.RequestException as e:
        logger.error(f"Failed to fetch RSS feed: {e}")
        raise
    except etree.ParseError as e:
        logger.error(f"Failed to parse RSS XML: {e}")
        raise RSSParsingError(f"Invalid RSS feed structure: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise