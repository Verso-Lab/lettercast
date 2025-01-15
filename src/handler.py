import os
import json
import logging
from core import PodcastAnalyzer, transform_audio, download_audio
from utils.logging_config import setup_logging

logger = logging.getLogger(__name__)

setup_logging()

def lambda_handler(event, context=None):
    """AWS Lambda handler for podcast analysis"""
    downloaded_file = None
    transformed_audio = None
    result_path = None
    
    try:
        # Get API key from environment
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
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
        
        try:
            # Process podcast (analyze, format, and save)
            logger.info("Processing podcast...")
            title = os.path.basename(audio_url)
            output_path = f"newsletters/lettercast_{os.path.splitext(title)[0]}.md"
            
            result_path = analyzer.process_podcast(
                transformed_audio,
                title=title,
                output_path=output_path
            )
            
            # Read the generated newsletter
            with open(result_path) as f:
                newsletter = f.read()
            
            # Return appropriate response based on context
            if context is None:
                logger.info(f"Newsletter saved to: {result_path}")
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'newsletter': newsletter,
                        'file_path': result_path
                    })
                }
            
            # Return Lambda response
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'newsletter': newsletter
                })
            }
            
        finally:
            # Cleanup transformed audio
            if transformed_audio and os.path.exists(transformed_audio):
                os.unlink(transformed_audio)
                
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
        # Cleanup downloaded file
        if downloaded_file and os.path.exists(downloaded_file):
            os.unlink(downloaded_file)
        # Cleanup result file if Lambda context
        if context is not None and result_path and os.path.exists(result_path):
            os.unlink(result_path)

def main():
    """CLI entry point"""
    try:
        audio_source = input("Enter URL or leave blank for default test: ").strip()
        if not audio_source:
            audio_source = "https://nyt.simplecastaudio.com/3026b665-46df-4d18-98e9-d1ce16bbb1df/episodes/13afee65-055d-4e1c-b6dc-66fd08977f03/audio/128/default.mp3"
        response = lambda_handler(audio_source)
        print("\nNewsletter generated successfully!")
        print(f"Saved to: {json.loads(response['body'])['file_path']}")
    except Exception as e:
        print(f"\nError: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()