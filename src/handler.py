import os
import json
import logging
from core import PodcastAnalyzer, transform_audio, format_newsletter
from utils import setup_lambda_logging

logger = setup_lambda_logging()

def lambda_handler(event, context):
    """AWS Lambda handler for podcast analysis"""
    try:
        # Get API key from environment
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        # Get audio URL from event
        if not event.get('audio_url'):
            raise ValueError("audio_url not provided in event")
        
        # TODO: Implement URL downloading
        audio_path = event['audio_url']  # This will be replaced with actual download
        
        # Initialize analyzer
        analyzer = PodcastAnalyzer(api_key)
        
        # Transform audio
        logger.info("Transforming audio...")
        transformed_audio = transform_audio(audio_path)
        
        try:
            # Analyze audio
            logger.info("Analyzing audio...")
            analysis = analyzer.analyze_audio_detailed(transformed_audio)
            
            # Create newsletter
            analyses = {os.path.basename(audio_path): analysis}
            newsletter = format_newsletter(analyses)
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'newsletter': newsletter
                })
            }
            
        finally:
            # Cleanup
            if os.path.exists(transformed_audio):
                os.unlink(transformed_audio)
                
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        } 