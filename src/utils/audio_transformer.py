import logging
import os
import tempfile
import time
from typing import Dict, List, Union, Tuple

from pydub import AudioSegment

from utils.logging_config import setup_logging

logger = logging.getLogger(__name__)
setup_logging()

class AudioTransformationError(Exception):
    """Base exception for audio transformation errors."""
    pass

def get_audio_length(audio_path: str) -> float:
    """Get audio file length in minutes.
    
    Args:
        audio_path: Path to audio file
        
    Returns:
        Length in minutes
        
    Raises:
        AudioTransformationError: If file cannot be loaded or length cannot be determined
    """
    try:
        audio = AudioSegment.from_file(audio_path)
        return len(audio) / (1000 * 60)  # Convert milliseconds to minutes
    except Exception as e:
        raise AudioTransformationError(f"Failed to get audio length: {str(e)}")

def chunk_audio(audio_path: str, chunk_minutes: int = 20) -> List[str]:
    """Split audio file into chunks of specified duration.
    
    Args:
        audio_path: Path to the audio file to chunk
        chunk_minutes: Duration of each chunk in minutes
        
    Returns:
        List of paths to chunked audio files
    """
    try:
        logger.info(f"Chunking audio file: {audio_path} into {chunk_minutes}-minute segments")
        
        # Load audio
        audio = AudioSegment.from_file(audio_path)
        
        # Calculate chunk size in milliseconds
        chunk_duration_ms = chunk_minutes * 60 * 1000
        total_duration_ms = len(audio)
        
        chunk_paths = []
        
        # Create chunks
        for i, start_ms in enumerate(range(0, total_duration_ms, chunk_duration_ms)):
            end_ms = min(start_ms + chunk_duration_ms, total_duration_ms)
            chunk = audio[start_ms:end_ms]
            
            # Create temporary file for chunk
            with tempfile.NamedTemporaryFile(
                suffix='.mp3',
                delete=False
            ) as tmp_file:
                logger.info(f"Exporting chunk {i+1} ({(end_ms-start_ms)/1000:.1f} seconds)")
                chunk.export(
                    tmp_file.name,
                    format='mp3',
                    parameters=["-q:a", "9"]
                )
                chunk_paths.append(tmp_file.name)
        
        logger.info(f"Created {len(chunk_paths)} chunks")
        return chunk_paths
        
    except Exception as e:
        logger.error(f"Failed to chunk audio: {str(e)}", exc_info=True)
        raise AudioTransformationError(f"Failed to chunk audio: {str(e)}") from None

def transform_audio(
    audio_path: str, 
    target_params: Dict = None,
    chunk_minutes: int = None
) -> Union[str, Tuple[str, List[str]]]:
    """Optimize audio file for Gemini API processing.
    
    Args:
        audio_path: Input audio file path
        target_params: Optional parameters, defaults to:
            {
                'channels': 1,          # Mono
                'frame_rate': 16000,    # 16kHz
                'format': 'mp3',        # Output format
                'quality': '9'          # MP3 quality (0-9)
            }
        chunk_minutes: Optional duration in minutes to split audio into chunks
            
    Returns:
        If chunk_minutes is None: Path to optimized audio file
        If chunk_minutes is set: Tuple[str, List[str]] containing (full_audio_path, chunk_paths)
            - If episode is shorter than chunk_minutes, chunk_paths will be empty
    """
    try:
        start_time = time.time()
        logger.info(f"Starting audio transformation for: {audio_path}")
        
        # Validate input
        if not audio_path:
            raise AudioTransformationError("Audio path cannot be empty")
        if not os.path.exists(audio_path):
            raise AudioTransformationError(f"Audio file not found: {audio_path}")
            
        # Set defaults
        target_params = target_params or {
            'channels': 1,
            'frame_rate': 16000,
            'format': 'mp3',
            'quality': '9'
        }
        
        # Log original size
        original_size = os.path.getsize(audio_path) / (1024 * 1024)
        logger.info(f"Original file size: {original_size:.2f} MB")
        
        try:
            # Load audio
            logger.info("Loading audio file...")
            audio = AudioSegment.from_file(audio_path)
            logger.info(f"Original audio: {audio.channels} channels, {audio.frame_rate}Hz")
        except Exception as e:
            raise AudioTransformationError(f"Failed to load audio file: {str(e)}")
        
        try:
            # Apply optimizations
            if audio.channels != target_params['channels']:
                audio = audio.set_channels(target_params['channels'])
                logger.info(f"Converted to {target_params['channels']} channel(s)")
            
            if audio.frame_rate != target_params['frame_rate']:
                audio = audio.set_frame_rate(target_params['frame_rate'])
                logger.info(f"Set frame rate to {target_params['frame_rate']}Hz")
        except Exception as e:
            raise AudioTransformationError(f"Failed to process audio: {str(e)}")
        
        try:
            # Export optimized file
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
                
                # If chunking is requested, check length and chunk if needed
                if chunk_minutes:
                    audio_length = get_audio_length(tmp_file.name)
                    if audio_length <= chunk_minutes:
                        logger.info(f"Audio length ({audio_length:.1f}m) <= chunk size ({chunk_minutes}m), skipping chunking")
                        return (tmp_file.name, [])
                    else:
                        logger.info(f"Proceeding to chunk audio into {chunk_minutes}-minute segments")
                        chunk_paths = chunk_audio(tmp_file.name, chunk_minutes)
                        return (tmp_file.name, chunk_paths)
                    
                return tmp_file.name
                
        except Exception as e:
            raise AudioTransformationError(f"Failed to export compressed audio: {str(e)}")
        
    except AudioTransformationError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in transform_audio: {str(e)}", exc_info=True)
        raise AudioTransformationError(f"Unexpected error: {str(e)}") from None 