import asyncio
import logging
import os
import pytz
from datetime import datetime, timedelta
from dotenv import load_dotenv
from sqlalchemy import select

from src.core.analyzer import PodcastAnalyzer
from src.core.scraper import get_recent_episodes
from src.database.config import AsyncSessionLocal
from src.database.models import Podcast
from src.utils.audio_transformer import get_audio_length, chunk_audio
from src.utils.logging_config import setup_logging
from src.utils.temp_file_context import download_audio_context

logger = logging.getLogger(__name__)
setup_logging()
load_dotenv()

def strip_articles(name: str) -> str:
    """Remove leading articles for sorting"""
    articles = ('the ', 'a ', 'an ')
    lower_name = name.lower()
    for article in articles:
        if lower_name.startswith(article):
            return name[len(article):]
    return name

async def select_podcast():
    """Select a podcast from alphabetically sorted list"""
    async with AsyncSessionLocal() as session:
        result = await session.exec(select(Podcast))
        podcasts = sorted(result.scalars().all(), key=lambda p: strip_articles(p.name))
        
        print("\nAvailable podcasts:")
        for i, podcast in enumerate(podcasts, 1):
            print(f"{i}. {podcast.name} ({podcast.category or 'no category'})")
        
        while True:
            try:
                choice = int(input("\nSelect a podcast (1-{}): ".format(len(podcasts))))
                if 1 <= choice <= len(podcasts):
                    return podcasts[choice - 1]
                print("Invalid choice. Please try again.")
            except ValueError:
                print("Please enter a number.")

def select_episode(episodes):
    """Select an episode from time-sorted list"""
    if not episodes:
        print("No episodes found in the last week.")
        return None
        
    # Sort episodes by publish date (newest first)
    sorted_episodes = sorted(episodes, key=lambda x: x['publish_date'], reverse=True)
    
    print("\nAvailable episodes from the last week:")
    for i, episode in enumerate(sorted_episodes, 1):
        local_time = episode['publish_date'].astimezone()
        publish_time = local_time.strftime('%a %m/%d/%y %H:%M %Z')
        print(f"{i}. [{publish_time}] {episode['title']}")
    
    while True:
        try:
            choice = int(input("\nSelect an episode (1-{}): ".format(len(sorted_episodes))))
            if 1 <= choice <= len(sorted_episodes):
                return sorted_episodes[choice - 1]
            print("Invalid choice. Please try again.")
        except ValueError:
            print("Please enter a number.")

async def main():
    """Test script for analyzing podcast episodes with Gemini"""
    try:
        # Get API key
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables or .env file")
        
        # Select podcast
        logger.info("Getting podcast list...")
        podcast = await select_podcast()
        
        # Get recent episodes
        all_episodes = get_recent_episodes(podcast)['episodes']
        
        # Filter for last week
        cutoff_time = datetime.now(pytz.UTC) - timedelta(days=7)
        recent_episodes = [
            ep for ep in all_episodes 
            if ep['publish_date'] >= cutoff_time
        ]
        
        # Select episode
        episode = select_episode(recent_episodes)
        if not episode:
            return
        
        # Process the episode
        print(f"\nProcessing episode: {episode['title']}")
        
        # Download and chunk audio
        with download_audio_context(episode['url']) as downloaded_file:
            # Get audio length and create chunks if needed
            audio_length = get_audio_length(downloaded_file)
            chunk_minutes = 20
            
            if audio_length <= chunk_minutes:
                logger.info(f"Episode length ({audio_length:.1f}m) <= chunk size ({chunk_minutes}m), skipping chunking")
                chunk_paths = []
            else:
                logger.info(f"Creating {chunk_minutes}-minute chunks...")
                chunk_paths = chunk_audio(downloaded_file, chunk_minutes)
                logger.info(f"Created {len(chunk_paths)} chunks")
            
            # Initialize analyzer
            analyzer = PodcastAnalyzer(api_key)
            
            # Process podcast with full audio and chunks (if any)
            newsletter = await analyzer.process_podcast(
                audio_path=downloaded_file,
                name=podcast.name,
                title=episode['title'],
                category=podcast.category or 'interview',
                publish_date=episode['publish_date'],
                prompt_addition=podcast.prompt_addition or '',
                episode_description=episode.get('episode_description', ''),
                chunk_paths=chunk_paths
            )
            
            # Clean up chunk files if any were created
            if chunk_paths:
                for path in chunk_paths:
                    if os.path.exists(path):
                        os.unlink(path)
            
            print("\nGenerated Newsletter:")
            print("=" * 80)
            print(newsletter)
            print("=" * 80)
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 