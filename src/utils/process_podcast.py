import asyncio
import logging
from dateutil import parser
from statistics import mean
from typing import Dict, Optional, Tuple

import requests
from lxml import etree

from src.core.scraper import RSSParsingError
from src.database import get_db, create_podcast, get_podcast_by_rss_url

CATEGORIES = ['banter', 'interview']

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
        """Fetch RSS feed and return channel element."""
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
        """Extract podcast metadata from RSS channel."""
        # Basic metadata
        name = channel.findtext('title', '').strip()
        description = channel.findtext('description', '')
        description = description or channel.findtext(f"{{{self.namespaces['itunes']}}}summary", '')
        
        # Image URL
        image_url = None
        image_elem = channel.find('image')
        if image_elem is not None:
            image_url = image_elem.findtext('url')
        if not image_url:
            image_url = channel.findtext(f"{{{self.namespaces['itunes']}}}image/[@href]")

        # Publisher
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

        return {
            "name": name,
            "description": description.strip() if description else None,
            "publisher": publisher,
            "image_url": image_url,
            "prompt_addition": None
        }

    def calculate_frequency(self, channel: etree.Element, max_episodes: int = 100) -> Optional[float]:
        """Calculate average episodes per week."""
        items = channel.findall('item')
        dates = []
        
        for item in items[:max_episodes]:
            pub_date = item.findtext('pubDate')
            if pub_date:
                try:
                    date = parser.parse(pub_date)
                    dates.append(date)
                except ValueError:
                    continue

        if len(dates) < 2:
            return None

        # Sort descending
        dates.sort(reverse=True)
        
        # Calculate average interval
        intervals = [(dates[i] - dates[i+1]).days for i in range(len(dates)-1)]
        avg_interval = mean(intervals)
        
        # Convert to weekly frequency
        episodes_per_week = 7.0 / avg_interval if avg_interval > 0 else None
        
        return round(episodes_per_week, 2) if episodes_per_week is not None else None

    def process_feed(self, rss_url: str, category: str) -> Dict:
        """Process RSS feed and return podcast data."""
        if category not in CATEGORIES:
            raise ValueError(f"Category must be one of: {', '.join(CATEGORIES)}")
            
        channel = self.fetch_and_parse_rss(rss_url)
        
        # Get metadata
        metadata = self.get_podcast_metadata(channel)
        frequency = self.calculate_frequency(channel)
        
        # Validate name
        if not metadata["name"]:
            raise RSSParsingError("Podcast name is required but was not found in the feed")
            
        # Combine data
        podcast_data = {
            **metadata,
            "rss_url": rss_url,
            "frequency": str(frequency) if frequency is not None else None,
            "category": category
        }
        
        return podcast_data

async def process_and_store_podcast(rss_url: str, category: str) -> Tuple[bool, str]:
    """Process podcast feed and store in database."""
    processor = PodcastProcessor()
    logger.info(f"Starting to process podcast from RSS URL: {rss_url}")
    
    try:
        async with get_db() as db:
            try:
                # Check existence
                logger.info("Checking if podcast already exists...")
                existing_podcast = await get_podcast_by_rss_url(db, rss_url)
                if existing_podcast:
                    logger.info(f"Podcast already exists with ID: {existing_podcast.id}")
                    return False, f"Podcast already exists with ID: {existing_podcast.id}"
                
                # Process and store
                logger.info("Processing RSS feed...")
                podcast_data = processor.process_feed(rss_url, category)
                logger.info(f"Successfully processed RSS feed. Podcast name: {podcast_data['name']}")
                
                logger.info("Creating podcast in database...")
                podcast = await create_podcast(db, podcast_data)
                logger.info(f"Created podcast object with ID: {podcast.id}")
                
                return True, f"Successfully created podcast: {podcast.name} (ID: {podcast.id})"
                
            except RSSParsingError as e:
                logger.error(f"RSS parsing error: {str(e)}")
                return False, f"Failed to process RSS feed: {str(e)}"
            except Exception as e:
                logger.error(f"Database operation error: {str(e)}", exc_info=True)
                await db.rollback()
                return False, f"Failed to create podcast in database: {str(e)}"
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}", exc_info=True)
        return False, f"Database connection error: {str(e)}"

async def main():
    """CLI entry point for podcast processing."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Process and store a podcast from RSS feed')
    parser.add_argument('rss_url', help='URL of the podcast RSS feed')
    args = parser.parse_args()
    
    # Category selection
    print("\nSelect podcast category:")
    for i, category in enumerate(CATEGORIES, 1):
        print(f"{i}. {category}")
    
    while True:
        try:
            choice = int(input("\nEnter number (1-{0}): ".format(len(CATEGORIES))))
            if 1 <= choice <= len(CATEGORIES):
                category = CATEGORIES[choice - 1]
                break
            print(f"Please enter a number between 1 and {len(CATEGORIES)}")
        except ValueError:
            print("Please enter a valid number")
    
    success, message = await process_and_store_podcast(args.rss_url, category)
    print(message)
    return 1 if not success else 0

if __name__ == "__main__":
    asyncio.run(main())