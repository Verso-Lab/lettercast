import os
from core import PodcastAnalyzer, transform_audio, format_newsletter, save_newsletter
from utils import setup_lambda_logging

def main():
    # Set up logging
    logger = setup_lambda_logging()
    
    # Get API key from environment
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    
    # Initialize analyzer
    analyzer = PodcastAnalyzer(api_key)
    
    # Process audio file
    audio_path = input("Enter path to audio file: ")
    
    try:
        # Transform audio
        logger.info("Transforming audio...")
        transformed_audio = transform_audio(audio_path)
        
        # Analyze audio
        logger.info("Analyzing audio...")
        analysis = analyzer.analyze_audio_detailed(transformed_audio)
        
        # Create newsletter
        analyses = {os.path.basename(audio_path): analysis}
        newsletter = format_newsletter(analyses)
        
        # Save newsletter
        output_path = save_newsletter(newsletter)
        logger.info(f"Newsletter saved to: {output_path}")
        
    finally:
        # Cleanup temporary file
        if os.path.exists(transformed_audio):
            os.unlink(transformed_audio)

if __name__ == "__main__":
    main() 