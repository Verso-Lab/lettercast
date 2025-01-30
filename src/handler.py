import os
import json
import logging
import pandas as pd
import uuid
from typing import List, Dict
from dotenv import load_dotenv
from core import PodcastAnalyzer, transform_audio, download_audio
from core.scraper import Podcast, get_recent_episodes
from utils.logging_config import setup_logging

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

def load_podcasts() -> List[Podcast]:
    """Load all podcasts from CSV file"""
    try:
        df = pd.read_csv('podcasts.csv')
        podcasts = []
        for _, row in df.iterrows():
            podcast = Podcast(
                id=str(row['id']) if pd.notna(row['id']) else str(uuid.uuid4()),
                podcast_name=row['name'],
                rss_url=row['rss_url'],
                publisher=row['publisher'] if pd.notna(row['publisher']) else None,
                description=row['description'] if pd.notna(row['description']) else None,
                image_url=row['image_url'] if pd.notna(row['image_url']) else None,
                frequency=row['frequency'] if pd.notna(row['frequency']) else None,
                tags=row['tags'] if pd.notna(row['tags']) else None
            )
            podcasts.append(podcast)
        return podcasts
    except Exception as e:
        logger.error(f"Failed to load podcasts: {e}")
        raise

def process_episode(podcast: Podcast, episode: Dict, api_key: str) -> Dict:
    """Process a single podcast episode"""
    downloaded_file = None
    transformed_audio = None
    result_path = None
    
    try:
        # Download audio file
        logger.info(f"Downloading episode: {episode['episode_name']} from {podcast.podcast_name}")
        downloaded_file = download_audio(episode['url'])
        
        # Transform audio
        logger.info("Transforming audio...")
        transformed_audio = transform_audio(downloaded_file)
        
        # Initialize analyzer
        analyzer = PodcastAnalyzer(api_key)
        
        # Create output directory structure
        os.makedirs(f"newsletters/{podcast.id}", exist_ok=True)
        
        # Process podcast
        logger.info(f"Processing episode: {episode['episode_name']}")
        result_path = f"newsletters/{podcast.id}/{episode['id']}_{episode['episode_name']}.md"
        
        analyzer.process_podcast(
            transformed_audio,
            title=episode['episode_name'],
            output_path=result_path
        )
        
        # Read the generated newsletter
        with open(result_path) as f:
            newsletter = f.read()
            
        return {
            'status': 'success',
            'podcast_id': podcast.id,
            'episode_id': episode['id'],
            'episode_name': episode['episode_name'],
            'output_path': result_path,
            'newsletter': newsletter
        }
        
    except Exception as e:
        logger.error(f"Failed to process episode {episode['id']}: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'podcast_id': podcast.id,
            'episode_id': episode['id'],
            'episode_name': episode['episode_name'],
            'error': str(e)
        }
        
    finally:
        cleanup_files(downloaded_file, transformed_audio, None, result_path)

def lambda_handler(event, context=None):
    """AWS Lambda handler for podcast processing"""
    results = []
    
    try:
        # Get API key
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables or .env file")
        
        # Handle single podcast case (from CLI)
        if isinstance(event, dict) and event.get('single_podcast'):
            podcast = event['podcast']
            logger.info(f"Processing single podcast: {podcast.podcast_name}")
            
            episodes = get_recent_episodes(podcast)
            if episodes['episodes']:
                latest_episode = episodes['episodes'][0]
                result = process_episode(podcast, latest_episode, api_key)
                results.append(result)
            else:
                logger.warning(f"No episodes found for podcast: {podcast.podcast_name}")
                results.append({
                    'status': 'error',
                    'podcast_id': podcast.id,
                    'error': 'No episodes found'
                })
        
        # Handle batch processing case (from Lambda)
        else:
            # Load all podcasts
            logger.info("Loading podcasts from CSV...")
            podcasts = load_podcasts()
            
            # Process each podcast's latest episode
            for podcast in podcasts:
                try:
                    logger.info(f"Checking for new episodes: {podcast.podcast_name}")
                    episodes = get_recent_episodes(podcast)
                    
                    if episodes['episodes']:
                        latest_episode = episodes['episodes'][0]
                        # TODO: Add check for new episode here
                        # For now, always process the latest episode
                        result = process_episode(podcast, latest_episode, api_key)
                        results.append(result)
                    else:
                        logger.warning(f"No episodes found for podcast: {podcast.podcast_name}")
                
                except Exception as e:
                    logger.error(f"Error processing podcast {podcast.podcast_name}: {str(e)}")
                    results.append({
                        'status': 'error',
                        'podcast_id': podcast.id,
                        'error': str(e)
                    })
                    continue
        
        if context is None:
            # Running locally
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'results': results
                }, default=str)
            }
        else:
            # In Lambda environment
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