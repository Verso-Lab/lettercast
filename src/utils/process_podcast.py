import asyncio
import logging
from datetime import datetime
from statistics import mean
from typing import Dict, List, Optional, Tuple

import pytz
import requests
from lxml import etree

from src.core.scraper import RSSParsingError
from src.database import get_db, create_podcast, get_podcast_by_rss_url

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PodcastProcessor:
    def __init__(self):
        self.parser = etree.XMLParser(recover=True)
        self.namespaces = {
            'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd',
            'content': 'http://purl.org/rss/1.0/modules/content/',
            'atom': 'http://www.w3.org/2005/Atom'
        }

    def fetch_and_parse_rss(self, rss_url: str) -> etree.Element:
        """Fetch and parse RSS feed, returning the channel element"""
        try:
            response = requests.get(rss_url, timeout=30)
            response.raise_for_status()
            
            root = etree.fromstring(response.content, self.parser)
            channel = root.find('channel')
            
            if channel is None:
                raise RSSParsingError("Invalid RSS feed - no channel element found")
            
            return channel
        except requests.RequestException as e:
            raise RSSParsingError(f"Failed to fetch RSS feed: {str(e)}")
        except etree.XMLSyntaxError as e:
            raise RSSParsingError(f"Failed to parse RSS feed: {str(e)}")

    def get_podcast_metadata(self, channel: etree.Element) -> Dict:
        """Extract all relevant podcast metadata from channel element"""
        # Get basic metadata
        name = channel.findtext('title', '').strip()
        description = channel.findtext('description', '')
        description = description or channel.findtext(f"{{{self.namespaces['itunes']}}}summary", '')
        
        # Get image URL (try different possible elements)
        image_url = None
        image_elem = channel.find('image')
        if image_elem is not None:
            image_url = image_elem.findtext('url')
        if not image_url:
            image_url = channel.findtext(f"{{{self.namespaces['itunes']}}}image/[@href]")

        # Get publisher (try different possible elements)
        publisher = None
        for elem in [
            f"{{{self.namespaces['itunes']}}}author",
            'managingEditor',
            'webMaster',
            'copyright'
        ]:
            publisher = channel.findtext(elem)
            if publisher and publisher.strip():
                publisher = publisher.strip()
                break

        # Get tags/categories
        tags = []
        for category in channel.findall(f"{{{self.namespaces['itunes']}}}category"):
            cat_text = category.get('text')
            if cat_text:
                tags.append(cat_text)
                # Get subcategories
                for subcat in category.findall(f"{{{self.namespaces['itunes']}}}category"):
                    subcat_text = subcat.get('text')
                    if subcat_text:
                        tags.append(f"{cat_text}/{subcat_text}")

        return {
            "name": name,
            "description": description.strip() if description else None,
            "publisher": publisher,
            "image_url": image_url,
            "tags": list(set(tags))  # Remove duplicates
        }

    def calculate_frequency(self, channel: etree.Element, max_episodes: int = 100) -> Optional[float]:
        """Calculate podcast publishing frequency as average episodes per week"""
        items = channel.findall('item')
        dates = []
        
        for item in items[:max_episodes]:
            pub_date = item.findtext('pubDate')
            if pub_date:
                try:
                    date = datetime.strptime(pub_date, '%a, %d %b %Y %H:%M:%S %z')
                    dates.append(date)
                except ValueError:
                    try:
                        # Try alternate format
                        date = datetime.strptime(pub_date, '%a, %d %b %Y %H:%M:%S %Z')
                        dates.append(date.replace(tzinfo=pytz.UTC))
                    except ValueError:
                        continue

        if len(dates) < 2:
            return None

        # Sort dates in descending order
        dates.sort(reverse=True)
        
        # Calculate average days between episodes
        intervals = [(dates[i] - dates[i+1]).days for i in range(len(dates)-1)]
        avg_interval = mean(intervals)
        
        # Convert to episodes per week (7 days / avg_interval)
        episodes_per_week = 7.0 / avg_interval if avg_interval > 0 else None
        
        return round(episodes_per_week, 2) if episodes_per_week is not None else None

    async def process_feed(self, rss_url: str) -> Dict:
        """Process RSS feed and return podcast data"""
        channel = self.fetch_and_parse_rss(rss_url)
        
        # Get all metadata
        metadata = self.get_podcast_metadata(channel)
        frequency = self.calculate_frequency(channel)
        
        # Combine all data
        podcast_data = {
            **metadata,
            "rss_url": rss_url,
            "frequency": frequency,
            "created_at": datetime.now(pytz.UTC),
            "updated_at": datetime.now(pytz.UTC)
        }
        
        return podcast_data

async def process_and_store_podcast(rss_url: str) -> Tuple[bool, str]:
    """Process podcast feed and store in database"""
    processor = PodcastProcessor()
    
    try:
        async with get_db() as db:
            # Check if podcast already exists
            existing_podcast = await get_podcast_by_rss_url(db, rss_url)
            if existing_podcast:
                return False, f"Podcast already exists with ID: {existing_podcast.id}"
            
            # Process feed and create podcast
            podcast_data = await processor.process_feed(rss_url)
            podcast = await create_podcast(db, podcast_data)
            await db.commit()
            
            return True, f"Successfully created podcast: {podcast.name} (ID: {podcast.id})"
    
    except RSSParsingError as e:
        return False, f"RSS parsing error: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

async def main():
    """CLI entry point"""
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python -m src.tasks.process_podcast <rss_url>")
        sys.exit(1)
    
    rss_url = sys.argv[1]
    success, message = await process_and_store_podcast(rss_url)
    print(message)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main()) 