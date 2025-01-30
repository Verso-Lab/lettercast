import requests
import logging
from datetime import datetime
from lxml import etree
import uuid
from typing import Dict, List, Optional
from dataclasses import dataclass
import pytz

logger = logging.getLogger(__name__)

@dataclass
class PodcastRow:
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

def get_recent_episodes(podcast: PodcastRow, limit: int = 5) -> Dict:
    """
    Fetch and parse the RSS feed for a podcast, returning the most recent episodes.
    
    Args:
        podcast: PodcastRow object containing podcast metadata
        limit: Number of most recent episodes to return
    
    Returns:
        Dict containing list of episode objects
    """
    try:
        logger.info(f"Fetching RSS feed for {podcast.name} from {podcast.rss_url}")
        
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
                
                episode = {
                    "id": str(uuid.uuid4()),
                    "podcast_id": podcast.id,
                    "rss_guid": rss_guid,
                    "title": item.findtext('title', '').strip(),
                    "publish_date": publish_date.isoformat(),
                    "summary": "",  # To be generated later
                    "created_at": datetime.now(pytz.UTC).isoformat()
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
    # Example usage
    import pandas as pd
    
    # Read podcasts CSV
    podcasts_df = pd.read_csv('podcasts.csv')
    
    # Convert first row to PodcastRow
    first_podcast = PodcastRow(
        id=podcasts_df.iloc[0]['id'] or str(uuid.uuid4()),
        name=podcasts_df.iloc[0]['name'],
        rss_url=podcasts_df.iloc[0]['rss_url'],
        publisher=podcasts_df.iloc[0]['publisher'],
        description=podcasts_df.iloc[0]['description'],
        image_url=podcasts_df.iloc[0]['image_url']
    )
    
    # Get recent episodes
    result = get_recent_episodes(first_podcast)
    print(f"Found {len(result['episodes'])} recent episodes") 
    for episode in result['episodes']:
        print(episode)