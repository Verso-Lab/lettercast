import os
from dotenv import load_dotenv
import google.generativeai as genai
from pathlib import Path
from pydub import AudioSegment
import tempfile
import logging
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class PodcastAnalyzer:
    def __init__(self):
        logger.info("Initializing PodcastAnalyzer")
        # Load environment variables
        load_dotenv()
        
        # Configure Gemini
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY not found in environment variables")
            raise ValueError("GEMINI_API_KEY not found in environment variables")
            
        genai.configure(api_key=api_key)
        logger.info("Gemini API configured successfully")
        
        # Create the model
        generation_config = {
            "temperature": 1,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
            "response_mime_type": "text/plain",
        }
        
        self.model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            generation_config=generation_config,
        )
        logger.info("Gemini model initialized")
    
    def transform_audio(self, audio_path):
        """Transform audio to reduce file size"""
        try:
            start_time = time.time()
            logger.info(f"Starting audio transformation for: {audio_path}")
            
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
            # Get original file size
            original_size = os.path.getsize(audio_path) / (1024 * 1024)
            logger.info(f"Original file size: {original_size:.2f} MB")
            
            try:
                # Load audio file
                logger.info("Loading audio file...")
                audio = AudioSegment.from_file(audio_path)
            except Exception as e:
                raise Exception(f"Failed to load audio file: {str(e)}")
            
            logger.info(f"Original audio: {audio.channels} channels, {audio.frame_rate}Hz")
            
            try:
                # Convert to mono
                audio = audio.set_channels(1)
                logger.info("Converted to mono")
                
                # Reduce sample rate to 16kHz
                audio = audio.set_frame_rate(16000)
                logger.info("Reduced sample rate to 16kHz")
            except Exception as e:
                raise Exception(f"Failed to process audio: {str(e)}")
            
            try:
                # Export with reduced quality
                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_file:
                    logger.info("Exporting compressed audio...")
                    audio.export(tmp_file.name, format='mp3', 
                               parameters=["-q:a", "9"])
                    
                    compressed_size = os.path.getsize(tmp_file.name) / (1024 * 1024)
                    reduction = ((original_size - compressed_size) / original_size) * 100
                    
                    logger.info(f"Compressed file size: {compressed_size:.2f} MB")
                    logger.info(f"Size reduction: {reduction:.1f}%")
                    logger.info(f"Transformation completed in {time.time() - start_time:.1f} seconds")
                    
                    return tmp_file.name
            except Exception as e:
                raise Exception(f"Failed to export compressed audio: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error in transform_audio: {str(e)}", exc_info=True)
            raise
    
    def analyze_audio(self, audio_path, prompt):
        """Analyze a podcast episode using Gemini"""
        transformed_audio_path = None
        try:
            logger.info(f"Starting analysis for: {audio_path}")
            logger.info(f"Using prompt: {prompt}")
            
            # Transform audio to reduce size
            transformed_audio_path = self.transform_audio(audio_path)
            
            # Read the transformed audio file
            logger.info("Reading transformed audio file...")
            audio_data = Path(transformed_audio_path).read_bytes()
            
            # Send the audio with the prompt
            logger.info("Sending audio to Gemini for analysis...")
            start_time = time.time()
            
            response = self.model.generate_content([
                prompt,
                {
                    "mime_type": "audio/mp3",
                    "data": audio_data
                }
            ])
            
            logger.info(f"Analysis completed in {time.time() - start_time:.1f} seconds")
            return response.text
                
        except Exception as e:
            logger.error(f"Error analyzing audio: {str(e)}", exc_info=True)
            return f"Error analyzing audio: {str(e)}"
            
        finally:
            # Clean up temporary file
            if transformed_audio_path and os.path.exists(transformed_audio_path):
                try:
                    logger.info("Cleaning up temporary files...")
                    os.unlink(transformed_audio_path)
                except Exception as e:
                    logger.error(f"Failed to clean up temporary file: {str(e)}")