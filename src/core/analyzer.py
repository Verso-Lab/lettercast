import hashlib
import logging
import os
import time
from datetime import datetime
from typing import Optional, List, Dict, Union
import asyncio

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from .prompts import BACKGROUND, PREANALYSIS_PROMPT, INTERVIEW_PROMPT, BANTER_PROMPT
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
    
    async def analyze_audio(
        self, 
        audio_path: str, 
        name: str, 
        category: str, 
        prompt_addition: str, 
        episode_description: str = "",
        chunk_context: Optional[str] = None,
        moment_count: int = 10,
        quote_count: int = 15,
        hook_count: int = 6
    ) -> str:
        """Generate detailed analysis of a podcast episode or chunk.
        
        Args:
            audio_path: Path to audio file
            name: Podcast name
            category: Podcast category (interview/banter)
            prompt_addition: Additional podcast context
            episode_description: Episode-specific description
            chunk_context: If analyzing a chunk, description of which part (e.g. "Part 1 of 3, 0-20 minutes")
            moment_count: Number of moments to analyze (fewer for chunks)
            quote_count: Number of quotes to extract (fewer for chunks)
            hook_count: Number of hooks to generate (fewer for chunks)
            
        Returns:
            Structured analysis text
        """
        logger.info(f"Starting analysis for: {audio_path}")
        start_time = time.time()
        
        try:
            # Check if file already exists in Gemini storage
            file_hash = self._get_file_hash(audio_path)
            
            # Run file listing in thread pool since it's synchronous
            existing_files = await asyncio.to_thread(genai.list_files)
            
            for existing_file in existing_files:
                gemini_hash = existing_file.sha256_hash.decode() if isinstance(existing_file.sha256_hash, bytes) else existing_file.sha256_hash
                if gemini_hash == file_hash:
                    logger.info("Found matching file in Gemini storage")
                    audio_file = existing_file
                    break
            else:
                logger.info("Uploading audio to Gemini...")
                # Run upload in thread pool
                audio_file = await asyncio.to_thread(genai.upload_file, audio_path)
            
            # Get initial insights from audio
            logger.info(f"Step 1: Pre-analysis from audio using {self.preanalysis_model.model_name}...")
            formatted_prompt = PREANALYSIS_PROMPT.format(
                name=name,
                prompt_addition=prompt_addition,
                background=BACKGROUND,
                chunk_context=chunk_context or "an episode",
                moment_count=moment_count,
                quote_count=quote_count,
                hook_count=hook_count
            )
            logger.info(f"Using prompt addition for analysis: {prompt_addition[:50]}..." if prompt_addition else "No prompt addition detected")
            
            # Run generate_content in thread pool
            preanalysis_response = await asyncio.to_thread(
                self.preanalysis_model.generate_content,
                [formatted_prompt, audio_file],
                safety_settings=self.SAFETY_SETTINGS
            )
            
            return preanalysis_response.text
                
        except Exception as e:
            if not isinstance(e, AnalyzerError):
                logger.error(f"Analysis failed: {str(e)}", exc_info=True)
                raise AnalyzerError(f"Analysis failed: {str(e)}") from None
            raise

    async def analyze_chunks(
        self,
        chunk_paths: List[str],
        name: str,
        category: str,
        prompt_addition: str,
        episode_description: str = ""
    ) -> List[str]:
        """Analyze multiple chunks of a podcast episode in parallel.
        
        Args:
            chunk_paths: List of paths to audio chunks
            name: Podcast name
            category: Podcast category
            prompt_addition: Additional podcast context
            episode_description: Episode description
            
        Returns:
            List of analysis texts, one per chunk
        """
        logger.info(f"Starting parallel chunk analysis for {len(chunk_paths)} chunks...")

        async def analyze_chunk(i: int, chunk_path: str) -> str:
            """Analyze a single chunk asynchronously."""
            logger.info(f"Analyzing chunk {i+1}/{len(chunk_paths)}: {chunk_path}")
            
            # Use smaller counts for chunk analysis
            chunk_analysis = await self.analyze_audio(
                audio_path=chunk_path,
                name=name,
                category=category,
                prompt_addition=prompt_addition,
                episode_description=episode_description,
                chunk_context=f"Part {i+1} of {len(chunk_paths)}, {i*20}-{(i+1)*20} minutes",
                moment_count=7,  # Reduced from 10
                quote_count=8,   # Reduced from 15
                hook_count=3     # Reduced from 6
            )
            logger.info(f"Completed analysis of chunk {i+1}/{len(chunk_paths)}")
            return chunk_analysis

        # Create tasks for all chunks and run them concurrently
        tasks = [analyze_chunk(i, chunk_path) for i, chunk_path in enumerate(chunk_paths)]
        chunk_analyses = await asyncio.gather(*tasks)
        
        logger.info(f"Completed parallel analysis of all {len(chunk_paths)} chunks")
        return chunk_analyses

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
    
    async def process_podcast(
        self,
        audio_path: str,
        name: str,
        title: str,
        category: str,
        publish_date: datetime,
        prompt_addition: str = "",
        episode_description: str = "",
        chunk_paths: Optional[List[str]] = None
    ) -> str:
        """Process podcast from audio to newsletter.
        
        Args:
            audio_path: Full audio file path (used only for final context)
            name: Podcast name
            title: Episode title
            category: Podcast category (interview/banter)
            publish_date: Episode publish date
            prompt_addition: Additional podcast context
            episode_description: Episode description
            chunk_paths: List of paths to audio chunks. If empty, will analyze full audio directly.
            
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
            
            # Get analyses based on whether we have chunks
            if chunk_paths and len(chunk_paths) > 0:
                logger.info(f"Processing {len(chunk_paths)} chunks...")
                analyses = await self.analyze_chunks(
                    chunk_paths=chunk_paths,
                    **analysis_params
                )
                logger.info(f"Completed analysis of {len(analyses)} chunks")
            else:
                logger.info("No chunks provided or episode too short, analyzing full audio...")
                analyses = [await self.analyze_audio(
                    audio_path=audio_path,
                    **analysis_params
                )]
                logger.info("Completed full audio analysis")
            
            # Select prompt based on podcast format
            if category == 'interview':
                prompt = INTERVIEW_PROMPT.format(
                    prompt_addition=prompt_addition,
                    episode_description=episode_description,
                    background=BACKGROUND,
                )
            elif category == 'banter':
                prompt = BANTER_PROMPT.format(
                    prompt_addition=prompt_addition,
                    episode_description=episode_description,
                    background=BACKGROUND,
                )
            else:
                logger.warning(f"Unknown podcast category: {category}, defaulting to interview prompt")
                prompt = INTERVIEW_PROMPT.format(
                    prompt_addition=prompt_addition,
                    episode_description=episode_description,
                    background=BACKGROUND,
                )
            
            # Generate newsletter using analyses and full audio
            logger.info("Generating final newsletter...")
            content_parts = [prompt]
            content_parts.extend(analyses)
            logger.info(f"Including {len(analyses)} analyses in final generation")
            
            # Add the full audio for final context
            audio_file = await asyncio.to_thread(genai.upload_file, audio_path)
            content_parts.append(audio_file)
            
            # Run generate_content in thread pool
            writing_response = await asyncio.to_thread(
                self.writing_model.generate_content,
                content_parts,
                safety_settings=self.SAFETY_SETTINGS
            )
            
            self.validate_analysis(writing_response.text)
            
            # Format newsletter with validated parameters
            return self.format_newsletter(
                analysis=writing_response.text,
                name=name,
                title=title,
                publish_date=publish_date
            )
            
        except Exception as e:
            if not isinstance(e, AnalyzerError):
                logger.error(f"Failed to process podcast: {str(e)}", exc_info=True)
                raise AnalyzerError(f"Failed to process podcast: {str(e)}") from None
            raise