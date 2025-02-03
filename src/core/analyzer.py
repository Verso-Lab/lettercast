import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from .prompts import PREANALYSIS_PROMPT, INTERVIEW_PROMPT, BANTER_PROMPT
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
    
    REQUIRED_SECTIONS = ['TLDR', 'Big picture', 'Highlights', 'Quoted', 'Worth your time if...']
    
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
        logger.info("Gemini model initialized")
    
    def _get_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of a file and return hex string."""
        import hashlib
        with open(file_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    
    def validate_analysis(self, analysis: str) -> None:
        """Validate that analysis contains required sections."""
        missing = [section for section in self.REQUIRED_SECTIONS if section not in analysis]
        if missing:
            logger.warning(f"Analysis missing required sections: {', '.join(missing)}")
    
    def analyze_audio(self, audio_path: str, name: str, category: str, prompt_addition: str) -> str:
        """Analyze a podcast episode and return detailed analysis.
        
        Args:
            audio_path: Path to the audio file to analyze
            name: Name of the podcast (not episode title)
            prompt_addition: Additional context about the podcast (e.g. description)
            
        Returns:
            str: Detailed analysis text
        """
        logger.info(f"Starting analysis for: {audio_path}")
        start_time = time.time()
        
        try:
            # Calculate file hash
            file_hash = self._get_file_hash(audio_path)
            
            # Check Gemini storage for matching file
            for existing_file in genai.list_files():
                gemini_hash = existing_file.sha256_hash.decode() if isinstance(existing_file.sha256_hash, bytes) else existing_file.sha256_hash
                if gemini_hash == file_hash:
                    logger.info("Found matching file in Gemini storage")
                    audio_file = existing_file
                    break
            else:
                logger.info("Uploading audio to Gemini...")
                audio_file = genai.upload_file(audio_path)
            
            # Step 1: Get initial insights
            logger.info("Step 1: Getting initial insights from audio...")
            formatted_prompt = PREANALYSIS_PROMPT.format(
                name=name,
                prompt_addition=prompt_addition
            )
            logger.info(f"Using prompt addition for analysis: {prompt_addition[:50]}..." if prompt_addition else "No prompt addition detected")
            
            insights = self.model.generate_content(
                [formatted_prompt, audio_file],
                safety_settings=self.SAFETY_SETTINGS
            ).text
            
            # Step 2: Generate newsletter
            logger.info("Step 2: Generating newsletter from insights and audio...")
            
            # Select appropriate prompt based on podcast category
            if category == 'interview':
                prompt = INTERVIEW_PROMPT
            elif category == 'banter':
                prompt = BANTER_PROMPT
            else:
                logger.warning(f"Unknown podcast category: {category}, defaulting to interview prompt")
                prompt = INTERVIEW_PROMPT
                
            analysis = self.model.generate_content(
                [prompt, insights, audio_file],
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
    
    def format_newsletter(self, analysis: str, name: Optional[str] = None, title: Optional[str] = None) -> str:
        """Format analysis into a newsletter.
        
        Args:
            analysis: The analysis text from analyze_audio
            name: Name of the podcast (not episode title)
            title: Title of the specific episode
            
        Returns:
            str: Formatted newsletter text
        """
        try:
            logger.info("Formatting newsletter...")
            
            today = datetime.now().strftime("%B %d, %Y")
            newsletter = f"{today} | {name}\n# {title}\n"
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
        output_path = output_path or f"newsletters/lettercast_{datetime.now().strftime('%Y%m%d')}.md"
        
        try:
            logger.info(f"Saving newsletter to: {output_path}")
            with open(output_path, 'w') as f:
                f.write(newsletter_text)
            return output_path
        except Exception as e:
            logger.error(f"Error saving newsletter: {str(e)}", exc_info=True)
            raise AnalyzerError(f"Failed to save newsletter: {str(e)}")
    
    def process_podcast(
        self,
        audio_path: str,
        name: str,
        prompt_addition: Optional[str] = None,
        title: Optional[str] = None,
        category: Optional[str] = None,
    ) -> str:
        """Process a podcast from audio to newsletter text.
        
        Args:
            audio_path: Path to the audio file to analyze
            name: Name of the podcast (not episode title)
            prompt_addition: Additional context about the podcast (e.g. description)
            title: Title of the specific episode
            category: Category of the podcast
            
        Returns:
            str: Formatted newsletter text
        """
        if not prompt_addition:
            logger.warning(f"No description found for podcast: {name}")
            prompt_addition = ""
        
        analysis = self.analyze_audio(audio_path, name=name, category=category, prompt_addition=prompt_addition)
        return self.format_newsletter(analysis, name, title)