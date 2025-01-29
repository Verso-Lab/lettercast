import os
import json
import logging
from dotenv import load_dotenv
from core import PodcastAnalyzer, transform_audio, download_audio
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

def lambda_handler(event, context=None):
    """AWS Lambda handler for podcast analysis"""
    downloaded_file = None
    transformed_audio = None
    result_path = None
    
    try:
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables or .env file")
        
        # Get audio URL from event or CLI input
        audio_url = event.get('audio_url') if isinstance(event, dict) else event
        if not audio_url:
            raise ValueError("audio_url not provided")
        
        # Download audio file
        logger.info("Downloading audio file...")
        downloaded_file = download_audio(audio_url)
        
        # Initialize analyzer
        analyzer = PodcastAnalyzer(api_key)
        
        # Transform audio
        logger.info("Transforming audio...")
        transformed_audio = transform_audio(downloaded_file)
        
        # Process podcast (analyze, format, and save)
        logger.info("Processing podcast...")
        title = os.path.basename(audio_url)
        output_path = f"newsletters/lettercast_{os.path.splitext(title)[0]}.md"
        
        result_path = analyzer.process_podcast(
            transformed_audio,
            episode_name=title,
            output_path=output_path
        )
        
        # Read the generated newsletter
        with open(result_path) as f:
            newsletter = f.read()
        
        if context is None:
            # Running locally
            logger.info(f"Newsletter saved to: {result_path}")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'newsletter': newsletter,
                    'file_path': result_path
                })
            }
        else:
            # In Lambda environment
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'newsletter': newsletter
                })
            }
            
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        if context is not None:
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': str(e)
                })
            }
        raise
        
    finally:
        cleanup_files(downloaded_file, transformed_audio, context, result_path)