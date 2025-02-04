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
    """Base exception for download-related errors."""
    pass

class FileSizeError(DownloadError):
    """Raised when file size exceeds limits."""
    pass

class DownloadTimeoutError(DownloadError):
    """Raised when download exceeds time limit."""
    pass

# Lambda execution constraints
DEFAULT_CONSTRAINTS = {
    'max_file_size_mb': 450,  # Max file size
    'max_download_seconds': 840,  # 14 minutes
    'chunk_size': 8192,  # Download buffer size
    'temp_dir': '/tmp'  # Lambda temp directory
}

def download_audio(
    url: str,
    constraints: Optional[Dict] = None,
    progress_bar: bool = True
) -> str:
    """Download audio file with Lambda execution constraints.
    
    Args:
        url: Audio file URL
        constraints: Optional constraints, defaults to:
            {
                'max_file_size_mb': 450,      # Max size in MB
                'max_download_seconds': 840,   # Max time in seconds
                'chunk_size': 8192,           # Buffer size
                'temp_dir': '/tmp'            # Temp directory
            }
        progress_bar: Show download progress
        
    Returns:
        Path to downloaded file
    """
    temp_path = None
    try:
        logger.info(f"Starting download from: {url}")
        start_time = time.time()
        
        # Apply constraints
        constraints = constraints or DEFAULT_CONSTRAINTS
        max_size = constraints.get('max_file_size_mb', DEFAULT_CONSTRAINTS['max_file_size_mb'])
        max_time = constraints.get('max_download_seconds', DEFAULT_CONSTRAINTS['max_download_seconds'])
        chunk_size = constraints.get('chunk_size', DEFAULT_CONSTRAINTS['chunk_size'])
        temp_dir = constraints.get('temp_dir', DEFAULT_CONSTRAINTS['temp_dir'])
        
        # Validate URL
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise DownloadError(f"Invalid URL: {url}")
        
        # Check file size
        try:
            response = requests.head(url, allow_redirects=True)
            total_size = int(response.headers.get('content-length', 0))
            
            # Try GET if HEAD fails
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
        
        # Create temp file
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
                # Setup progress bar
                if progress_bar:
                    pbar = tqdm(
                        total=total_size,
                        unit='iB',
                        unit_scale=True,
                        unit_divisor=1024,
                        desc=f"Downloading {os.path.basename(parsed.path)}",
                        miniters=1
                    )
                
                # Download chunks
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        # Check time limit
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