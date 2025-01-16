import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from pathlib import Path
import logging
import time
from datetime import datetime
from typing import Optional, Tuple
from .prompts import PODCAST_ANALYSIS_STEP1_PROMPT, PODCAST_ANALYSIS_STEP2_PROMPT
from utils.logging_config import setup_logging

logger = logging.getLogger(__name__)
setup_logging()

class AnalyzerError(Exception):
    """Base class for analyzer-related errors"""
    pass

class InvalidAnalysisError(AnalyzerError):
    """Raised when analysis content is invalid or missing required sections"""
    pass

class PodcastAnalyzer:
    SAFETY_SETTINGS = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH
    }
    
    REQUIRED_SECTIONS = ['TLDR', 'BIG PICTURE', 'HIGHLIGHTS', 'QUOTED', 'WORTH YOUR TIME IF']
    
    def __init__(self, api_key):
        """Initialize the analyzer with a Gemini API key"""
        logger.info("Initializing PodcastAnalyzer")
        
        if not api_key:
            logger.error("GEMINI_API_KEY not provided")
            raise ValueError("GEMINI_API_KEY not provided")
            
        genai.configure(api_key=api_key)
        logger.info("Gemini API configured successfully")
        
        # Create the model
        generation_config = {
            "temperature": 1,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
        }
        
        self.model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            generation_config=generation_config,
        )
        
        # Cache of file hashes and sizes to avoid re-uploading
        self.file_cache = {}
        self.file_sizes = {}
        logger.info("Gemini model initialized")
    
    def _get_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of a file and return hex string."""
        import hashlib
        with open(file_path, "rb") as f:
            file_bytes = f.read()
            self.file_sizes[file_path] = len(file_bytes)
            return hashlib.sha256(file_bytes).hexdigest()
    
    def validate_analysis(self, analysis: str) -> None:
        """Validate that analysis contains required sections."""
        missing = [section for section in self.REQUIRED_SECTIONS if section not in analysis]
        if missing:
            raise InvalidAnalysisError(
                f"Analysis missing required sections: {', '.join(missing)}"
            )
    
    def analyze_audio(self, audio_path: str) -> str:
        """Analyze a podcast episode and return detailed analysis."""
        logger.info(f"Starting analysis for: {audio_path}")
        start_time = time.time()
        
        try:
            # Calculate file hash and size
            file_hash = self._get_file_hash(audio_path)
            logger.info(f"File hash: {file_hash}")
            
            # Check if we've seen this file before
            if file_hash in self.file_cache:
                logger.info("Using cached file from Gemini storage")
                audio_file = self.file_cache[file_hash]
            else:
                # Check Gemini storage for matching file
                for existing_file in genai.list_files():
                    gemini_hash = existing_file.sha256_hash.decode() if isinstance(existing_file.sha256_hash, bytes) else existing_file.sha256_hash
                    if gemini_hash == file_hash:
                        self.file_cache[file_hash] = existing_file
                        audio_file = existing_file
                        logger.info("Using matching file in Gemini storage")
                        break
                else:
                    logger.info("Uploading audio to Gemini...")
                    audio_file = genai.upload_file(audio_path)
                    self.file_cache[file_hash] = audio_file
            
            # Step 1: Get initial insights
            logger.info("Step 1: Getting initial insights from audio...")
            insights = self.model.generate_content(
                [PODCAST_ANALYSIS_STEP1_PROMPT, audio_file],
                safety_settings=self.SAFETY_SETTINGS
            ).text
            
            # Step 2: Generate newsletter
            logger.info("Step 2: Generating newsletter from insights and audio...")
            analysis = self.model.generate_content(
                [PODCAST_ANALYSIS_STEP2_PROMPT, insights, audio_file],
                safety_settings=self.SAFETY_SETTINGS
            ).text
            
            self.validate_analysis(analysis)
            logger.info(f"Analysis completed in {time.time() - start_time:.1f} seconds")
            return analysis
                
        except Exception as e:
            if not isinstance(e, AnalyzerError):
                logger.error(f"Analysis failed: {str(e)}", exc_info=True)
                raise AnalyzerError(f"Analysis failed: {str(e)}") from None
            raise
    
    def format_newsletter(self, analysis: str, title: Optional[str] = None) -> str:
        """Format analysis into a newsletter."""
        try:
            logger.info("Formatting newsletter...")
            self.validate_analysis(analysis)
            
            today = datetime.now().strftime("%B %d, %Y")
            newsletter = f"# Lettercast\n#### {today}\n\n"
            
            if title:
                newsletter += f"## {title}\n\n"
            
            newsletter += analysis
            
            logger.info("Newsletter formatting complete")
            return newsletter
        
        except InvalidAnalysisError:
            raise
        except Exception as e:
            logger.error(f"Error formatting newsletter: {str(e)}", exc_info=True)
            raise AnalyzerError(f"Failed to format newsletter: {str(e)}")
    
    def save_newsletter(self, newsletter_text: str, output_path: Optional[str] = None) -> str:
        """Save newsletter to a file."""
        try:
            if not output_path:
                output_path = f"newsletters/lettercast_{datetime.now().strftime('%Y%m%d')}.md"
            
            logger.info(f"Saving newsletter to: {output_path}")
            with open(output_path, 'w') as f:
                f.write(newsletter_text)
            
            return output_path
        
        except Exception as e:
            logger.error(f"Error saving newsletter: {str(e)}", exc_info=True)
            raise AnalyzerError(f"Failed to save newsletter: {str(e)}")
    
    def process_podcast(self, audio_path: str, title: Optional[str] = None, output_path: Optional[str] = None) -> str:
        """Process a podcast from audio to saved newsletter."""
        try:
            analysis = self.analyze_audio(audio_path)
            newsletter = self.format_newsletter(analysis, title)
            return self.save_newsletter(newsletter, output_path)
        except AnalyzerError:
            raise
        except Exception as e:
            logger.error(f"Error processing podcast: {str(e)}", exc_info=True)
            raise AnalyzerError(f"Failed to process podcast: {str(e)}") from None