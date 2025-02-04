import os
from contextlib import contextmanager
import copy

from utils.downloader import download_audio, DEFAULT_CONSTRAINTS
from utils.audio_transformer import transform_audio

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
def transform_audio_context(audio_path):
    """Transform audio file and clean up after use.
    
    Args:
        audio_path: Path to input audio file
        
    Yields:
        Path to transformed file
    """
    file_path = transform_audio(audio_path)
    try:
        yield file_path
    finally:
        if file_path and os.path.exists(file_path):
            os.unlink(file_path) 