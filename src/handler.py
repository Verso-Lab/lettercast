import json
import logging
import os
from datetime import datetime
from typing import Dict, List

import pytz
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession

from core import PodcastAnalyzer, download_audio, transform_audio
from core.scraper import get_recent_episodes
from src.database import crud
from src.database.config import AsyncSessionLocal
from utils.logging_config import setup_logging
from src.database.models import Podcast

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

async def load_podcasts(db: AsyncSession) -> List[Podcast]:
    """Load all podcasts from database"""
    try:
        return await crud.list_podcasts(db)
    except Exception as e:
        logger.error(f"Failed to load podcasts: {e}")
        raise

async def find_unprocessed_episodes(db: AsyncSession, podcast: Podcast, rss_episodes: List[Dict], minutes: int) -> List[Dict]:
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

async def process_episode(db: AsyncSession, podcast: Podcast, episode: Dict, api_key: str) -> Dict:
    """Process a single podcast episode"""
    downloaded_file = None
    transformed_audio = None
    
    try:
        # Download audio file
        logger.info(f"Downloading episode: {episode['title']} from {podcast.name}")
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
            name=podcast.name,
            prompt_addition=podcast.prompt_addition,
            title=episode['title']
        )
        
        # Create episode in database with newsletter as summary
        episode_data = {
            'podcast_id': podcast.id,
            'rss_guid': episode['rss_guid'],
            'title': episode['title'],
            'publish_date': datetime.fromisoformat(episode['publish_date']),
            'summary': newsletter
        }
        await crud.create_episode(db, episode_data)
        await db.commit()

        result = {
            'status': 'success',
            'podcast_id': podcast.id,
            'episode_id': episode['id'],
            'title': episode['title'],
            'newsletter': newsletter
        }
        logger.info(f"Episode {episode['title']} processed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Failed to process episode {episode['id']}: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'podcast_id': podcast.id,
            'episode_id': episode['id'],
            'title': episode['title'],
            'error': str(e)
        }
        
    finally:
        cleanup_files(downloaded_file, transformed_audio, None, None)

async def lambda_handler(event=None, context=None):
    """AWS Lambda handler for podcast processing. Runs every X minutes via EventBridge."""
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
            
            total_podcasts = len(podcasts)
            total_new_episodes = 0
            successful_processes = 0
            failed_processes = 0
            errors = []
            
            # Process each podcast's new episodes
            for podcast in podcasts:
                try:
                    logger.info(f"Checking for new episodes: {podcast.name}")
                    
                    # Get episodes from RSS
                    rss_episodes = get_recent_episodes(podcast)['episodes']
                    # Find which ones aren't in our database and are within time window
                    unprocessed = await find_unprocessed_episodes(db, podcast, rss_episodes, minutes)
                    
                    total_new_episodes += len(unprocessed)
                    
                    if unprocessed:
                        for episode in unprocessed:
                            result = await process_episode(db, podcast, episode, api_key)
                            if result['status'] == 'success':
                                successful_processes += 1
                            else:
                                failed_processes += 1
                                errors.append({
                                    'podcast': podcast.name,
                                    'episode': episode['title'],
                                    'error': result['error']
                                })
                    else:
                        logger.info(f"No new episodes found for podcast: {podcast.name}")
                
                except Exception as e:
                    logger.error(f"Error processing podcast {podcast.name}: {str(e)}")
                    failed_processes += 1
                    errors.append({
                        'podcast': podcast.name,
                        'error': str(e)
                    })
                    continue
        
        summary = {
            'time_window_minutes': minutes,
            'total_podcasts_checked': total_podcasts,
            'new_episodes_found': total_new_episodes,
            'successfully_processed': successful_processes,
            'failed_processes': failed_processes,
            'run_timestamp': datetime.now(pytz.UTC).isoformat()
        }
        
        if errors:
            summary['errors'] = errors[:10]  # Limit to first 10 errors to keep response size reasonable
            if len(errors) > 10:
                summary['additional_errors_count'] = len(errors) - 10
        
        return {
            'statusCode': 200,
            'body': json.dumps(summary, default=str)
        }
            
    except Exception as e:
        logger.error(f"Handler failed: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'time_window_minutes': minutes if 'minutes' in locals() else None,
                'run_timestamp': datetime.now(pytz.UTC).isoformat()
            }, default=str)
        }