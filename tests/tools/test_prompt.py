import os
import logging
import asyncio
from dotenv import load_dotenv
from datetime import datetime
import pytz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.analyzer import PodcastAnalyzer
from src.utils.audio_transformer import transform_audio
from src.utils.logging_config import setup_logging
from src.database.models import Podcast
from src.database.config import AsyncSessionLocal

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

async def select_podcast():
    """Select a podcast to use for metadata"""
    async with AsyncSessionLocal() as session:
        result = await session.exec(select(Podcast))
        podcasts = result.scalars().all()
        
        print("\nWhich podcast is this episode from?:")
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

async def main():
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
            
        # Select podcast for metadata
        podcast = await select_podcast()
        
        # Transform audio for Gemini
        logger.info("Sending audio for transformation...")
        transformed_audio = transform_audio(audio_path)
        
        # Initialize analyzer
        analyzer = PodcastAnalyzer(api_key)
        
        # Process podcast
        title = os.path.basename(audio_path)
        
        # Get episode description from user
        episode_description = input("\nEnter episode description (optional, press Enter to skip): ").strip()
        
        # Analyze and print
        newsletter = analyzer.process_podcast(
            audio_path=transformed_audio,
            name=podcast.name,
            title=title,
            category=podcast.category or 'interview',  # Default to interview if not set
            publish_date=datetime.now(pytz.UTC),
            prompt_addition=podcast.prompt_addition or '',
            episode_description=episode_description
        )
        
        print("\nGenerated Newsletter:")
        print("=" * 80)
        print(newsletter)
        print("=" * 80)
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        exit(1)
    finally:
        # Cleanup transformed audio file
        if transformed_audio and os.path.exists(transformed_audio):
            os.unlink(transformed_audio)

if __name__ == "__main__":
    asyncio.run(main()) 