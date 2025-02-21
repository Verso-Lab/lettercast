import json
import logging
import os
from datetime import datetime
from typing import Dict, List

import asyncio
from dotenv import load_dotenv
import pytz

from sqlalchemy.ext.asyncio import AsyncSession

from core import PodcastAnalyzer
from core.scraper import get_recent_episodes
from src.database import crud
from src.database.config import AsyncSessionLocal
from src.database.models import Podcast
from src.utils.audio_transformer import get_audio_length, chunk_audio
from src.utils.logging_config import setup_logging
from src.utils.temp_file_context import download_audio_context

logger = logging.getLogger(__name__)

setup_logging()
load_dotenv()

API_KEY = os.getenv('GEMINI_API_KEY')
if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

GLOBAL_ANALYZER = PodcastAnalyzer(API_KEY)

def cleanup_files(downloaded_file, transformed_audio, context, result_path):
    """Clean up temporary files, respecting Lambda context."""
    if transformed_audio and os.path.exists(transformed_audio):
        os.unlink(transformed_audio)
    if downloaded_file and os.path.exists(downloaded_file):
        os.unlink(downloaded_file)
    if context is not None and result_path and os.path.exists(result_path):
        os.unlink(result_path)

async def load_podcasts(db: AsyncSession) -> List[Podcast]:
    """Fetch all podcasts from database."""
    try:
        return await crud.list_podcasts(db)
    except Exception as e:
        logger.error(f"Failed to load podcasts: {e}")
        raise

async def find_unprocessed_episodes(db: AsyncSession, podcast: Podcast, rss_episodes: List[Dict], minutes: int) -> List[Dict]:
    """Find new episodes within time window.
    
    Args:
        db: Database session
        podcast: Podcast to check
        rss_episodes: Episodes from RSS feed
        minutes: Time window in minutes
        
    Returns:
        List of unprocessed episodes
    """
    unprocessed = []
    now = datetime.now(pytz.UTC)
    
    episodes_in_window = 0
    new_episodes = 0
    
    for episode in rss_episodes:
        # Check time window
        publish_date = episode['publish_date']
        if isinstance(publish_date, str):
            try:
                publish_date = datetime.fromisoformat(publish_date.replace('Z', '+00:00'))
            except ValueError as e:
                logger.error(f"Failed to parse publish date {publish_date}: {e}")
                continue
                
        time_diff = now - publish_date
        if time_diff.total_seconds() > minutes * 60:
            continue
            
        episodes_in_window += 1
        
        # Check database
        existing = await crud.get_episode_by_guid(db, episode['rss_guid'])
        if not existing:
            unprocessed.append(episode)
            new_episodes += 1
    
    logger.info(
        f"Found {episodes_in_window} episodes within {minutes} minute window for {podcast.name}, of which {new_episodes} are new"
    )
    
    return unprocessed

async def process_episode(
    db: AsyncSession, podcast: Podcast, episode: Dict
) -> Dict:
    """Process single episode using context managers.
    
    Args:
        db: Database session
        podcast: Parent podcast
        episode: Episode data from RSS
        
    Returns:
        Processing result with status
    """
    try:
        logger.info("Downloading episode: %s from %s", episode['title'], podcast.name)
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
            
            # Process the podcast with full audio and chunks (if any)
            newsletter = await GLOBAL_ANALYZER.process_podcast(
                audio_path=downloaded_file,
                name=podcast.name,
                title=episode['title'],
                category=podcast.category if hasattr(podcast, 'category') else 'interview',
                publish_date=datetime.fromisoformat(episode['publish_date']) if isinstance(episode['publish_date'], str) else episode['publish_date'],
                prompt_addition=podcast.prompt_addition,
                episode_description=episode.get('episode_description', ""),
                chunk_paths=chunk_paths
            )
            
            episode_data = {
                'podcast_id': podcast.id,
                'rss_guid': episode['rss_guid'],
                'title': episode['title'],
                'publish_date': datetime.fromisoformat(episode['publish_date']) if isinstance(episode['publish_date'], str) else episode['publish_date'],
                'summary': newsletter
            }
            await crud.create_episode(db, episode_data)
            await db.commit()

            # Clean up chunk files if any were created
            if chunk_paths:
                for path in chunk_paths:
                    if os.path.exists(path):
                        os.unlink(path)

            result = {
                'status': 'success',
                'podcast_id': podcast.id,
                'episode_id': episode['id'],
                'title': episode['title'],
                'newsletter': newsletter
            }
            logger.info("Episode %s processed successfully", episode['title'])
            return result
    except Exception as e:
        logger.error("Failed to process episode %s: %s", episode['id'], str(e), exc_info=True)
        return {
            'status': 'error',
            'podcast_id': podcast.id,
            'episode_id': episode['id'],
            'title': episode['title'],
            'error': str(e)
        }

async def process_episode_concurrent(podcast: Podcast, episode: Dict) -> Dict:
    """Process episode with dedicated database session."""
    async with AsyncSessionLocal() as local_db:
        return await process_episode(local_db, podcast, episode)

async def lambda_handler(event=None, context=None):
    """Process new podcast episodes from the last hour.
    
    Runs on a schedule via EventBridge to:
    1. Load all podcasts
    2. Check each for new episodes
    3. Process new episodes concurrently
    4. Generate newsletters
    
    Returns:
        Processing summary with status and counts
    """
    try:
        # Default to last hour
        minutes = int(os.getenv('CHECK_MINUTES', '60'))
        logger.info("Processing episodes from last %d minutes", minutes)

        async with AsyncSessionLocal() as db:
            logger.info("Loading podcasts from database...")
            podcasts = await crud.list_podcasts(db)

        total_podcasts = len(podcasts)
        total_new_episodes = 0
        successful_processes = 0
        failed_processes = 0
        errors = []

        # Process each podcast one at a time
        for podcast in podcasts:
            # First get RSS episodes
            rss_episodes = get_recent_episodes(podcast)['episodes']
            
            # Then check which episodes are new/unprocessed
            async with AsyncSessionLocal() as db:
                unprocessed = await find_unprocessed_episodes(db, podcast, rss_episodes, minutes)

            total_new_episodes += len(unprocessed)

            if unprocessed:
                logger.info(f"Processing {len(unprocessed)} episodes for podcast: {podcast.name}")
                for episode in unprocessed:
                    logger.info(f"Starting to process episode: {episode.get('title')} from {podcast.name}")
                    try:
                        result = await process_episode_concurrent(podcast, episode)
                        if result.get('status') == 'success':
                            successful_processes += 1
                        else:
                            failed_processes += 1
                            errors.append({
                                'podcast': podcast.name,
                                'episode': result.get('title', 'Unknown'),
                                'error': result.get('error', 'Unknown error')
                            })
                    except Exception as e:
                        failed_processes += 1
                        errors.append({
                            'podcast': podcast.name,
                            'error': str(e)
                        })
            else:
                logger.info("No new episodes found for podcast: %s", podcast.name)

        summary = {
            'time_window_minutes': minutes,
            'total_podcasts_checked': total_podcasts,
            'new_episodes_found': total_new_episodes,
            'successfully_processed': successful_processes,
            'failed_processes': failed_processes,
            'run_timestamp': datetime.now(pytz.UTC).isoformat()
        }

        if errors:
            summary['errors'] = errors[:10]
            if len(errors) > 10:
                summary['additional_errors_count'] = len(errors) - 10

        if not os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
            print("\nRun completed. Summary:")
            print(json.dumps(summary, indent=2, default=str))

        return {
            'statusCode': 200,
            'body': json.dumps(summary, default=str)
        }

    except Exception as e:
        logger.error("Handler failed: %s", str(e), exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'time_window_minutes': minutes if 'minutes' in locals() else None,
                'run_timestamp': datetime.now(pytz.UTC).isoformat()
            }, default=str)
        }
