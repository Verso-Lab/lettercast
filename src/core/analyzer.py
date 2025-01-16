import os
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from pathlib import Path
import logging
import time
from datetime import datetime
from typing import Optional
from .prompts import PODCAST_ANALYSIS_PROMPT
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
        logger.info("Gemini model initialized")
    
    def validate_analysis(self, analysis: str) -> None:
        """Validate that analysis contains required sections."""
        missing = [section for section in self.REQUIRED_SECTIONS if section not in analysis]
        if missing:
            raise InvalidAnalysisError(
                f"Analysis missing required sections: {', '.join(missing)}"
            )
    
    def analyze_audio(self, audio_path: str) -> str:
        """Analyze a podcast episode and return detailed analysis."""
        try:
            logger.info(f"Starting analysis for: {audio_path}")
            audio_data = Path(audio_path).read_bytes()
            
            logger.info("Sending audio to Gemini for analysis...")
            start_time = time.time()
            
            response = self.model.generate_content([
                PODCAST_ANALYSIS_PROMPT,
                {
                    "mime_type": "audio/mp3",
                    "data": audio_data
                }
            ])
            response = self.model.generate_content(
                [PODCAST_ANALYSIS_PROMPT, audio_file],
                safety_settings=self.SAFETY_SETTINGS
            )
            
            analysis = response.text
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