import copy
import os
import logging

from contextlib import contextmanager

from utils.downloader import download_audio, DEFAULT_CONSTRAINTS
from utils.audio_transformer import transform_audio, get_audio_length

logger = logging.getLogger(__name__)

@contextmanager
def download_audio_context(url, chunk_size=8192):
    """Download audio file and clean up after use.
    
    Args:
        url: Audio file URL
        chunk_size: Download chunk size in bytes
        
    Yields:
        Path to downloaded file
    """
    # Create a constraints dictionary based on DEFAULT_CONSTRAINTS from downloader,
    # and override the 'chunk_size' with the provided parameter.
    constraints = copy.deepcopy(DEFAULT_CONSTRAINTS)
    constraints['chunk_size'] = chunk_size
    file_path = download_audio(url, constraints=constraints)
    try:
        yield file_path
    finally:
        if file_path and os.path.exists(file_path):
            os.unlink(file_path)

@contextmanager
def transform_audio_context(audio_path, chunk_minutes: int = None):
    """Transform audio file and clean up after use.
    
    Args:
        audio_path: Path to input audio file
        chunk_minutes: Optional duration in minutes to split audio into chunks
        
    Yields:
        If chunk_minutes is None: Path to transformed file
        If chunk_minutes is set: Tuple[str, List[str]] containing (full_audio_path, chunk_paths)
            - If episode is shorter than chunk_minutes, chunk_paths will be empty
    """
    try:
        # Always transform the full audio first
        full_audio_path = transform_audio(audio_path)
        
        if not chunk_minutes:
            # Non-chunked case
            yield full_audio_path
        else:
            # Get audio length in minutes
            audio_length = get_audio_length(full_audio_path)
            
            if audio_length <= chunk_minutes:
                # Episode too short to chunk
                logger.info(f"Episode length ({audio_length:.1f}m) <= chunk size ({chunk_minutes}m), skipping chunking")
                yield (full_audio_path, [])
            else:
                # Create chunks from the transformed audio
                chunk_paths = transform_audio(full_audio_path, chunk_minutes=chunk_minutes)
                yield (full_audio_path, chunk_paths)
            
        # Clean up
        if os.path.exists(full_audio_path):
            os.unlink(full_audio_path)
            
        if chunk_minutes and 'chunk_paths' in locals():
            for path in chunk_paths:
                if path and os.path.exists(path):
                    os.unlink(path)
                    
    except Exception as e:
        # Clean up on error
        if 'full_audio_path' in locals() and os.path.exists(full_audio_path):
            os.unlink(full_audio_path)
        if chunk_minutes and 'chunk_paths' in locals():
            for path in chunk_paths:
                if path and os.path.exists(path):
                    os.unlink(path)
        raise 