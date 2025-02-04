import logging
import os
import requests
import tempfile
import time
from tqdm import tqdm
from typing import Dict, Optional
from urllib.parse import urlparse

from utils.logging_config import setup_logging

logger = logging.getLogger(__name__)

setup_logging()

class DownloadError(Exception):
    """Base exception for download-related errors"""
    pass

class FileSizeError(DownloadError):
    """Raised when file size exceeds limits"""
    pass

class DownloadTimeoutError(DownloadError):
    """Raised when download exceeds time limit"""
    pass

# Default Lambda constraints
DEFAULT_CONSTRAINTS = {
    'max_file_size_mb': 450,  # Leave buffer for other files
    'max_download_seconds': 840,  # 14 minutes, leaving 1-min buffer
    'chunk_size': 8192,
    'temp_dir': '/tmp'  # Lambda's temp directory
}

def download_audio(
    url: str,
    constraints: Optional[Dict] = None,
    progress_bar: bool = True
) -> str:
    """Download audio file from URL to a temporary file.
    
    Args:
        url: URL of the audio file to download
        constraints: Optional dictionary of constraints. Defaults to:
            {
                'max_file_size_mb': 450,      # Maximum file size in MB
                'max_download_seconds': 840,   # Maximum download time in seconds
                'chunk_size': 8192,           # Download chunk size
                'temp_dir': '/tmp'            # Temporary directory for downloads
            }
        progress_bar: Whether to show progress bar, defaults to True
        
    Returns:
        str: Path to the downloaded temporary file
        
    Raises:
        DownloadError: Base class for all download-related errors
        FileSizeError: If file size exceeds constraints
        DownloadTimeoutError: If download exceeds time limit
    """
    temp_path = None
    try:
        logger.info(f"Starting download from: {url}")
        start_time = time.time()
        
        # Set constraints
        constraints = constraints or DEFAULT_CONSTRAINTS
        max_size = constraints.get('max_file_size_mb', DEFAULT_CONSTRAINTS['max_file_size_mb'])
        max_time = constraints.get('max_download_seconds', DEFAULT_CONSTRAINTS['max_download_seconds'])
        chunk_size = constraints.get('chunk_size', DEFAULT_CONSTRAINTS['chunk_size'])
        temp_dir = constraints.get('temp_dir', DEFAULT_CONSTRAINTS['temp_dir'])
        
        # Validate URL
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise DownloadError(f"Invalid URL: {url}")
        
        # Get file size
        try:
            response = requests.head(url, allow_redirects=True)
            total_size = int(response.headers.get('content-length', 0))
            
            # If HEAD request doesn't return size, try GET with stream
            if total_size == 0:
                response = requests.get(url, stream=True, allow_redirects=True)
                total_size = int(response.headers.get('content-length', 0))
            
            size_mb = total_size / (1024 * 1024)
            
            if size_mb > max_size:
                raise FileSizeError(
                    f"File size ({size_mb:.1f}MB) exceeds limit of {max_size}MB"
                )
            
            logger.info(f"File size: {size_mb:.1f}MB")
            
        except requests.RequestException as e:
            raise DownloadError(f"Failed to check file size: {str(e)}")
        
        # Create temporary file
        try:
            suffix = os.path.splitext(parsed.path)[1] or '.mp3'
            temp_file = tempfile.NamedTemporaryFile(
                suffix=suffix,
                delete=False,
                dir=temp_dir
            )
            temp_path = temp_file.name
            
        except OSError as e:
            raise DownloadError(f"Failed to create temporary file: {str(e)}")
        
        # Download file
        try:
            if response.request.method != 'GET':
                response = requests.get(url, stream=True, allow_redirects=True)
            response.raise_for_status()
            
            downloaded = 0
            with temp_file:
                # Setup progress bar if requested
                if progress_bar:
                    pbar = tqdm(
                        total=total_size,
                        unit='iB',
                        unit_scale=True,
                        unit_divisor=1024,
                        desc=f"Downloading {os.path.basename(parsed.path)}",
                        miniters=1
                    )
                
                # Download in chunks
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        # Check timeout
                        if time.time() - start_time > max_time:
                            raise DownloadTimeoutError(
                                f"Download exceeded {max_time}s time limit"
                            )
                        
                        size = len(chunk)
                        temp_file.write(chunk)
                        downloaded += size
                        
                        if progress_bar:
                            pbar.update(size)
                
                if progress_bar:
                    pbar.close()
            
            logger.info(f"Download completed in {time.time() - start_time:.1f}s")
            return temp_path
            
        except requests.RequestException as e:
            raise DownloadError(f"Download failed: {str(e)}")
    
    except DownloadError:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
        raise
    except Exception as e:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
        logger.error(f"Unexpected error during download: {str(e)}", exc_info=True)
        raise DownloadError(f"Unexpected error: {str(e)}") from None 