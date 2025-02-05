import hashlib
import logging
import os
import time
from datetime import datetime
from typing import Optional

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from .prompts import PREANALYSIS_PROMPT, INTERVIEW_PROMPT, BANTER_PROMPT
from utils.logging_config import setup_logging

logger = logging.getLogger(__name__)
setup_logging()

class AnalyzerError(Exception):
    """Base exception for analyzer-related errors"""
    pass

class InvalidAnalysisError(AnalyzerError):
    """Raised when analysis is missing required sections"""
    pass

class PodcastAnalyzer:
    SAFETY_SETTINGS = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH
    }
    
    REQUIRED_SECTIONS = ['TLDR', 'The big picture', 'Highlights', 'Quoted', 'Worth your time if']
    
    def __init__(self, api_key):
        """Initialize analyzer with Gemini API credentials"""
        logger.info("Initializing PodcastAnalyzer")
        
        if not api_key:
            logger.error("GEMINI_API_KEY not provided")
            raise ValueError("GEMINI_API_KEY not provided")
            
        genai.configure(api_key=api_key)
        logger.info("Gemini API configured successfully")
        
        # Configure model parameters
        preanalysis_config = {
            "temperature": 0.5,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
        }
        
        writing_config = {
            "temperature": 0.8,
            "top_p": 0.95,
            "top_k": 80,
            "max_output_tokens": 8192,
        }
        
        # Initialize models for different tasks
        self.preanalysis_model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-thinking-exp",
            generation_config=preanalysis_config,
        )
        self.writing_model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            generation_config=writing_config,
        )
        logger.info("Gemini models initialized")
    
    def _get_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of a file"""
        with open(file_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    
    def validate_analysis(self, analysis: str) -> None:
        """Check if analysis contains all required sections"""
        missing = [section for section in self.REQUIRED_SECTIONS if section not in analysis]
        if missing:
            logger.warning(f"Analysis missing required sections: {', '.join(missing)}")
    
    def analyze_audio(self, audio_path: str, name: str, category: str, prompt_addition: str, episode_description: str = "") -> str:
        """Generate detailed analysis of a podcast episode.
        
        Args:
            audio_path: Path to audio file
            name: Podcast name
            category: Podcast category (interview/banter)
            prompt_addition: Additional podcast context
            episode_description: Episode-specific description
            
        Returns:
            Structured analysis text
        """
        logger.info(f"Starting analysis for: {audio_path}")
        start_time = time.time()
        
        try:
            # Check if file already exists in Gemini storage
            file_hash = self._get_file_hash(audio_path)
            for existing_file in genai.list_files():
                gemini_hash = existing_file.sha256_hash.decode() if isinstance(existing_file.sha256_hash, bytes) else existing_file.sha256_hash
                if gemini_hash == file_hash:
                    logger.info("Found matching file in Gemini storage")
                    audio_file = existing_file
                    break
            else:
                logger.info("Uploading audio to Gemini...")
                audio_file = genai.upload_file(audio_path)
            
            # Get initial insights from audio
            logger.info(f"Step 1: Pre-analysis from audio using {self.preanalysis_model.model_name}...")
            formatted_prompt = PREANALYSIS_PROMPT.format(
                name=name,
                prompt_addition=prompt_addition
            )
            logger.info(f"Using prompt addition for analysis: {prompt_addition[:50]}..." if prompt_addition else "No prompt addition detected")
            
            preanalysis_response = self.preanalysis_model.generate_content(
                [formatted_prompt, audio_file],
                safety_settings=self.SAFETY_SETTINGS
            ).text
            
            # Generate newsletter from insights
            logger.info(f"Step 2: Writing newsletter from pre-analysis and audio using {self.writing_model.model_name}...")
            logger.info(f"Using episode description: {episode_description[:50]}..." if episode_description else "No episode description detected")
            
            # Select prompt based on podcast format
            if category == 'interview':
                prompt = INTERVIEW_PROMPT.format(episode_description=episode_description)
            elif category == 'banter':
                prompt = BANTER_PROMPT.format(episode_description=episode_description)
            else:
                logger.warning(f"Unknown podcast category: {category}, defaulting to interview prompt")
                prompt = INTERVIEW_PROMPT.format(episode_description=episode_description)
                
            writing_response = self.writing_model.generate_content(
                [prompt, preanalysis_response, audio_file],
                safety_settings=self.SAFETY_SETTINGS
            ).text
            
            self.validate_analysis(writing_response)
            logger.info(f"Analysis completed in {time.time() - start_time:.1f} seconds")
            return writing_response
                
        except Exception as e:
            if not isinstance(e, AnalyzerError):
                logger.error(f"Analysis failed: {str(e)}", exc_info=True)
                raise AnalyzerError(f"Analysis failed: {str(e)}") from None
            raise
    
    def format_newsletter(self, analysis: str, name: str, title: str, publish_date: datetime) -> str:
        """Format analysis into newsletter template.
        
        Args:
            analysis: Analysis text from analyze_audio
            name: Podcast name
            title: Episode title
            publish_date: Episode publish date
            
        Returns:
            Formatted newsletter text
        """
        try:
            logger.info("Formatting newsletter...")
            
            if not analysis:
                raise AnalyzerError("Analysis text cannot be empty")
            if not name:
                raise AnalyzerError("Podcast name cannot be empty")
            if not title:
                raise AnalyzerError("Episode title cannot be empty")
            
            date_str = publish_date.strftime("%B %d, %Y")
            newsletter = f"{date_str} | {name}\n# {title}\n"
            newsletter += analysis
            
            logger.info("Newsletter formatting complete")
            return newsletter
        
        except InvalidAnalysisError:
            raise
        except Exception as e:
            logger.error(f"Error formatting newsletter: {str(e)}", exc_info=True)
            raise AnalyzerError(f"Failed to format newsletter: {str(e)}")
    
    def save_newsletter(self, newsletter_text: str, output_path: Optional[str] = None) -> str:
        """Save newsletter to file, using default path if none provided"""
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
        title: str,
        category: str,
        publish_date: datetime,
        prompt_addition: str = "",
        episode_description: str = "",
    ) -> str:
        """Process podcast from audio to newsletter.
        
        Args:
            audio_path: Audio file path
            name: Podcast name
            title: Episode title
            category: Podcast category (interview/banter)
            publish_date: Episode publish date
            prompt_addition: Additional podcast context
            episode_description: Episode description
            
        Returns:
            Formatted newsletter text
        """
        try:
            # Validate inputs
            required_params = {
                'audio_path': audio_path,
                'name': name,
                'title': title,
                'category': category,
                'publish_date': publish_date,
            }
            missing_params = [k for k, v in required_params.items() if not v]
            if missing_params:
                raise AnalyzerError(f"Missing required parameters: {', '.join(missing_params)}")
                
            if not os.path.exists(audio_path):
                raise AnalyzerError(f"Audio file not found: {audio_path}")
                
            # Normalize optional parameters
            analysis_params = {
                'name': name,
                'category': category,
                'prompt_addition': prompt_addition or "",
                'episode_description': episode_description or ""
            }
            
            # Log missing context
            if not prompt_addition:
                logger.warning(f"No prompt addition found for podcast: {name}")
            if not episode_description:
                logger.warning(f"No episode description found for podcast: {name}")
            
            # Get analysis using normalized parameters
            analysis = self.analyze_audio(
                audio_path,
                **analysis_params
            )
            
            # Format newsletter with validated parameters
            return self.format_newsletter(
                analysis=analysis,
                name=name,
                title=title,
                publish_date=publish_date
            )
            
        except Exception as e:
            if not isinstance(e, AnalyzerError):
                logger.error(f"Failed to process podcast: {str(e)}", exc_info=True)
                raise AnalyzerError(f"Failed to process podcast: {str(e)}") from None
            raise