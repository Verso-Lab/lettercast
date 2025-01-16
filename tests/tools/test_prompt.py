import os
import logging
from dotenv import load_dotenv
from core import PodcastAnalyzer, transform_audio
from utils.logging_config import setup_logging

logger = logging.getLogger(__name__)
setup_logging()
load_dotenv()

def get_audio_files():
    """Get list of audio files from audio directory"""
    audio_dir = "audio"
    if not os.path.exists(audio_dir):
        logger.warning(f"Directory {audio_dir} not found. Creating it...")
        os.makedirs(audio_dir)
        return []
    
    audio_files = []
    for file in os.listdir(audio_dir):
        if file.endswith(('.mp3', '.m4a', '.wav', '.aac')):
            audio_files.append(os.path.join(audio_dir, file))
    return sorted(audio_files)

def select_audio_file():
    """Present audio file options to user and get selection"""
    audio_files = get_audio_files()
    
    if not audio_files:
        logger.info("No audio files found in audio/ directory")
        return input("Enter path to local audio file: ").strip()
    
    print("\nAvailable audio files:")
    for i, file in enumerate(audio_files, 1):
        print(f"{i}. {os.path.basename(file)}")
    print("0. Enter custom path")
    
    while True:
        try:
            choice = int(input("\nSelect an option (0-{}): ".format(len(audio_files))))
            if choice == 0:
                return input("Enter path to local audio file: ").strip()
            elif 1 <= choice <= len(audio_files):
                return audio_files[choice - 1]
            else:
                print("Invalid choice. Please try again.")
        except ValueError:
            print("Please enter a number.")

def main():
    """Test script for analyzing local audio files with Gemini"""
    transformed_audio = None
    try:
        # Get API key
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables or .env file")
        
        # Get audio file path from user
        audio_path = select_audio_file()
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Transform audio for Gemini
        logger.info("Sending audio for transformation...")
        transformed_audio = transform_audio(audio_path)
        
        # Initialize analyzer
        analyzer = PodcastAnalyzer(api_key)
        
        # Process podcast
        title = os.path.basename(audio_path)
        output_path = f"newsletters/lettercast_{os.path.splitext(title)[0]}.md"
        
        # Analyze and save
        result_path = analyzer.process_podcast(
            transformed_audio,
            title=title,
            output_path=output_path
        )
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        exit(1)
    finally:
        # Cleanup transformed audio file
        if transformed_audio and os.path.exists(transformed_audio):
            os.unlink(transformed_audio)

if __name__ == "__main__":
    main() 