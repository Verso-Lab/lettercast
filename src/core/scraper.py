import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import pytz
import requests
from lxml import etree

logger = logging.getLogger(__name__)

@dataclass
class Podcast:
    id: str
    name: str
    rss_url: str
    publisher: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    frequency: Optional[str] = None
    tags: Optional[List[str]] = None

class RSSParsingError(Exception):
    """Raised when there's an error parsing the RSS feed"""
    pass

def parse_datetime(date_str: str) -> datetime:
    """Parse various datetime formats and return UTC timestamp"""
    try:
        # Try common RSS date formats
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
        
        # If none of the formats match, try parsing with dateutil
        from dateutil import parser
        dt = parser.parse(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=pytz.UTC)
        return dt
    except Exception as e:
        logger.warning(f"Failed to parse date {date_str}: {e}")
        return datetime.now(pytz.UTC)

def get_recent_episodes(podcast: Podcast, limit: int = 5) -> Dict:
    """
    Fetch and parse the RSS feed for a podcast, returning the most recent episodes.
    
    Args:
        podcast: PodcastRow object containing podcast metadata
        limit: Number of most recent episodes to return
    
    Returns:
        Dict containing list of episode objects
    """
    try:
        logger.info(f"Scraping RSS feed for {podcast.name} from {podcast.rss_url}")
        
        # Fetch RSS feed
        response = requests.get(podcast.rss_url, timeout=30)
        response.raise_for_status()
        
        # Parse XML
        parser = etree.XMLParser(recover=True)  # Recover from errors if possible
        root = etree.fromstring(response.content, parser=parser)
        
        # Handle different RSS namespaces
        namespaces = {
            'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd',
            'content': 'http://purl.org/rss/1.0/modules/content/',
            'atom': 'http://www.w3.org/2005/Atom'
        }
        
        # Find channel and items
        channel = root.find('channel')
        if channel is None:
            raise RSSParsingError("Invalid RSS feed - no channel element found")
            
        items = channel.findall('item')
        if not items:
            raise RSSParsingError("No episodes found in feed")
        
        # Process most recent episodes
        episodes = []
        for item in items[:limit]:
            try:
                # Extract guid, fallback to link if no guid
                guid = item.find('guid')
                rss_guid = guid.text if guid is not None else item.findtext('link')
                
                # Get publish date
                pub_date = item.findtext('pubDate')
                if pub_date:
                    publish_date = parse_datetime(pub_date)
                else:
                    publish_date = datetime.now(pytz.UTC)
                
                # Extract audio URL from enclosure
                audio_url = None
                enclosure = item.find('enclosure')
                if enclosure is not None:
                    audio_url = enclosure.get('url')
                    mime_type = enclosure.get('type', '')
                    if not audio_url or not mime_type.startswith('audio/'):
                        # Try finding another enclosure with audio type
                        for enc in item.findall('enclosure'):
                            if enc.get('type', '').startswith('audio/'):
                                audio_url = enc.get('url')
                                break
                
                if not audio_url:
                    logger.warning(f"No audio URL found for episode: {item.findtext('title', '')}")
                    continue
                
                episode = {
                    "id": str(uuid.uuid4()),
                    "podcast_id": podcast.id,
                    "name": podcast.name,
                    "rss_guid": rss_guid,
                    "title": item.findtext('title', '').strip(),
                    "publish_date": publish_date.isoformat(),
                    "summary": "",  # To be generated later
                    "created_at": datetime.now(pytz.UTC).isoformat(),
                    "url": audio_url
                }
                
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

if __name__ == "__main__":
    import pandas as pd
    
    podcasts_df = pd.read_csv('podcasts.csv')
    
    for index, row in podcasts_df.iterrows():
        podcast = Podcast(
            id=row['id'] if pd.notna(row['id']) else str(uuid.uuid4()),
            name=row['name'],
            rss_url=row['rss_url'],
            publisher=row['publisher'],
            description=row['description'],
            image_url=row['image_url'],
            frequency=row['frequency'],
            tags=row['tags'],
        )
        
        # Get recent episodes
        result = get_recent_episodes(podcast)
        print(f"Found {len(result['episodes'])} recent episodes") 
        print(result['episodes'][0])