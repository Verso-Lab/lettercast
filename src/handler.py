import os
import json
import logging
import pytz
from datetime import datetime
from typing import List, Dict
from dotenv import load_dotenv
from core import PodcastAnalyzer, transform_audio, download_audio
from core.scraper import Podcast, get_recent_episodes
from utils.logging_config import setup_logging
from src.database import crud
from src.database.config import AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

setup_logging()
load_dotenv()

def cleanup_files(downloaded_file, transformed_audio, context, result_path):
    """Delete files if they exist; respect Lambda context constraints."""
    # Cleanup transformed audio
    if transformed_audio and os.path.exists(transformed_audio):
        os.unlink(transformed_audio)
    # Cleanup downloaded file
    if downloaded_file and os.path.exists(downloaded_file):
        os.unlink(downloaded_file)
    # Cleanup result file if Lambda context
    if context is not None and result_path and os.path.exists(result_path):
        os.unlink(result_path)

def dict_to_podcast(podcast_dict: Dict) -> Podcast:
    """Convert a database dictionary to a Podcast object"""
    return Podcast(
        id=podcast_dict['id'],
        name=podcast_dict['name'],
        rss_url=podcast_dict['rss_url'],
        publisher=podcast_dict.get('publisher'),
        description=podcast_dict.get('description'),
        image_url=podcast_dict.get('image_url'),
        frequency=podcast_dict.get('frequency'),
        tags=podcast_dict.get('tags')
    )

async def load_podcasts(db: AsyncSession) -> List[Dict]:
    """Load all podcasts from database"""
    try:
        return await crud.list_podcasts(db)
    except Exception as e:
        logger.error(f"Failed to load podcasts: {e}")
        raise

async def find_unprocessed_episodes(db: AsyncSession, podcast: Dict, rss_episodes: List[Dict], minutes: int) -> List[Dict]:
    """Find episodes from RSS that don't exist in our database and are within time window"""
    unprocessed = []
    now = datetime.now(pytz.UTC)
    
    for episode in rss_episodes:
        # Check if episode is within time window
        publish_date = episode['publish_date']
        if isinstance(publish_date, str):
            try:
                # If it's ISO format string, parse it
                publish_date = datetime.fromisoformat(publish_date.replace('Z', '+00:00'))
            except ValueError as e:
                logger.error(f"Failed to parse publish date {publish_date}: {e}")
                continue
                
        time_diff = now - publish_date
        if time_diff.total_seconds() > minutes * 60:
            continue
        
        # Check if episode exists in database
        existing = await crud.get_episode_by_guid(db, episode['rss_guid'])
        if not existing:
            unprocessed.append(episode)
    
    return unprocessed

async def process_episode(db: AsyncSession, podcast: Dict, episode: Dict, api_key: str) -> Dict:
    """Process a single podcast episode"""
    downloaded_file = None
    transformed_audio = None
    
    try:
        # Download audio file
        logger.info(f"Downloading episode: {episode['title']} from {podcast['name']}")
        downloaded_file = download_audio(episode['url'])
        
        # Transform audio
        logger.info("Transforming audio...")
        transformed_audio = transform_audio(downloaded_file)
        
        # Initialize analyzer
        analyzer = PodcastAnalyzer(api_key)
        
        # Process podcast
        logger.info(f"Processing episode: {episode['title']}")
        newsletter = analyzer.process_podcast(
            audio_path=transformed_audio,
            name=podcast['name'],
            description=podcast['description'],
            title=episode['title']
        )
        
        # Create episode in database with newsletter as summary
        episode_data = {
            'podcast_id': podcast['id'],
            'rss_guid': episode['rss_guid'],
            'title': episode['title'],
            'publish_date': datetime.fromisoformat(episode['publish_date']),
            'summary': newsletter
        }
        await crud.create_episode(db, episode_data)
        await db.commit()
            
        return {
            'status': 'success',
            'podcast_id': podcast['id'],
            'episode_id': episode['id'],
            'title': episode['title'],
            'newsletter': newsletter
        }
        
    except Exception as e:
        logger.error(f"Failed to process episode {episode['id']}: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'podcast_id': podcast['id'],
            'episode_id': episode['id'],
            'title': episode['title'],
            'error': str(e)
        }
        
    finally:
        cleanup_files(downloaded_file, transformed_audio, None, None)

async def lambda_handler(event=None, context=None):
    """AWS Lambda handler for podcast processing. Runs every X minutes via EventBridge."""
    results = []
    
    try:
        # Get API key
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        # Default to checking last 60 minutes
        minutes = int(os.getenv('CHECK_MINUTES', '60'))
        logger.info(f"Processing episodes from last {minutes} minutes")
        
        async with AsyncSessionLocal() as db:
            # Load all podcasts
            logger.info("Loading podcasts from database...")
            podcasts = await load_podcasts(db)
            
            # Process each podcast's new episodes
            for podcast_dict in podcasts:
                try:
                    logger.info(f"Checking for new episodes: {podcast_dict['name']}")
                    
                    # Convert dictionary to Podcast object for scraper
                    podcast = dict_to_podcast(podcast_dict)
                    
                    # Get episodes from RSS
                    rss_episodes = get_recent_episodes(podcast)['episodes']
                    # Find which ones aren't in our database and are within time window
                    unprocessed = await find_unprocessed_episodes(db, podcast_dict, rss_episodes, minutes)
                    
                    if unprocessed:
                        for episode in unprocessed:
                            result = await process_episode(db, podcast_dict, episode, api_key)
                            results.append(result)
                    else:
                        logger.info(f"No new episodes found for podcast: {podcast_dict['name']}")
                
                except Exception as e:
                    logger.error(f"Error processing podcast {podcast_dict['name']}: {str(e)}")
                    results.append({
                        'status': 'error',
                        'podcast_id': podcast_dict['id'],
                        'error': str(e)
                    })
                    continue
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'results': results
            }, default=str)
        }
            
    except Exception as e:
        logger.error(f"Handler failed: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'partial_results': results
            }, default=str)
        }