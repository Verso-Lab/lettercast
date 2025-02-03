import logging
import os
import tempfile
import time
from typing import Dict

from pydub import AudioSegment

from utils.logging_config import setup_logging

logger = logging.getLogger(__name__)
setup_logging()

class AudioTransformationError(Exception):
    """Base exception for audio transformation errors"""
    pass

def transform_audio(audio_path: str, target_params: Dict = None) -> str:
    """Transform audio to reduce file size and optimize for Gemini API.
    
    Args:
        audio_path: Path to the input audio file
        target_params: Optional dictionary of target parameters. Defaults to:
            {
                'channels': 1,          # Mono audio
                'frame_rate': 16000,    # 16kHz sample rate
                'format': 'mp3',        # Output format
                'quality': '9'          # MP3 quality (0-9, 9 being lowest)
            }
            
    Returns:
        str: Path to the transformed audio file
        
    Raises:
        AudioTransformationError: If any step of the transformation fails
    """
    try:
        start_time = time.time()
        logger.info(f"Starting audio transformation for: {audio_path}")
        
        # Validate input file
        if not audio_path:
            raise AudioTransformationError("Audio path cannot be empty")
        if not os.path.exists(audio_path):
            raise AudioTransformationError(f"Audio file not found: {audio_path}")
            
        # Set default parameters if none provided
        target_params = target_params or {
            'channels': 1,
            'frame_rate': 16000,
            'format': 'mp3',
            'quality': '9'
        }
        
        # Get original file size
        original_size = os.path.getsize(audio_path) / (1024 * 1024)
        logger.info(f"Original file size: {original_size:.2f} MB")
        
        try:
            # Load audio file
            logger.info("Loading audio file...")
            audio = AudioSegment.from_file(audio_path)
            logger.info(f"Original audio: {audio.channels} channels, {audio.frame_rate}Hz")
        except Exception as e:
            raise AudioTransformationError(f"Failed to load audio file: {str(e)}")
        
        try:
            # Apply transformations
            if audio.channels != target_params['channels']:
                audio = audio.set_channels(target_params['channels'])
                logger.info(f"Converted to {target_params['channels']} channel(s)")
            
            if audio.frame_rate != target_params['frame_rate']:
                audio = audio.set_frame_rate(target_params['frame_rate'])
                logger.info(f"Set frame rate to {target_params['frame_rate']}Hz")
        except Exception as e:
            raise AudioTransformationError(f"Failed to process audio: {str(e)}")
        
        try:
            # Export with target parameters
            with tempfile.NamedTemporaryFile(
                suffix=f'.{target_params["format"]}',
                delete=False
            ) as tmp_file:
                logger.info("Exporting compressed audio...")
                audio.export(
                    tmp_file.name,
                    format=target_params['format'],
                    parameters=["-q:a", target_params['quality']]
                )
                
                # Log results
                compressed_size = os.path.getsize(tmp_file.name) / (1024 * 1024)
                reduction = ((original_size - compressed_size) / original_size) * 100
                
                logger.info(f"Compressed file size: {compressed_size:.2f} MB")
                logger.info(f"Size reduction: {reduction:.1f}%")
                logger.info(f"Transformation completed in {time.time() - start_time:.1f} seconds")
                
                return tmp_file.name
                
        except Exception as e:
            raise AudioTransformationError(f"Failed to export compressed audio: {str(e)}")
        
    except AudioTransformationError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in transform_audio: {str(e)}", exc_info=True)
        raise AudioTransformationError(f"Unexpected error: {str(e)}") from None 