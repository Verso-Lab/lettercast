import logging
import os
import requests
import tempfile
import time
from pathlib import Path
from tqdm import tqdm
from urllib.parse import urlparse

from utils.logging_config import setup_logging

logger = logging.getLogger(__name__)

setup_logging()

# Lambda constraints
MAX_FILE_SIZE_MB = 450  # Leave buffer for other files
MAX_DOWNLOAD_SECONDS = 840  # 14 minutes, leaving 1-min buffer

def download_audio(url, chunk_size=8192):
    """Download audio file from URL to a temporary file.
    
    Args:
        url (str): URL of the audio file to download
        chunk_size (int): Size of chunks to download at a time
        
    Returns:
        str: Path to the downloaded temporary file
        
    Raises:
        ValueError: If URL is invalid or file too large
        TimeoutError: If download exceeds Lambda timeout
        requests.RequestException: If download fails
    """
    try:
        logger.info(f"Starting download from: {url}")
        start_time = time.time()
        
        # Validate URL
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid URL: {url}")
        
        # Check file size before downloading
        response = requests.head(url, allow_redirects=True)
        total_size = int(response.headers.get('content-length', 0))
        
        # If HEAD request doesn't return size, try GET with stream
        if total_size == 0:
            response = requests.get(url, stream=True, allow_redirects=True)
            total_size = int(response.headers.get('content-length', 0))
        
        size_mb = total_size / (1024 * 1024)
        
        if size_mb > MAX_FILE_SIZE_MB:
            raise ValueError(
                f"File size ({size_mb:.1f}MB) exceeds Lambda limit of {MAX_FILE_SIZE_MB}MB"
            )
        
        logger.info(f"File size: {size_mb:.1f}MB")
        
        # Create temporary file
        suffix = os.path.splitext(parsed.path)[1] or '.mp3'
        temp_file = tempfile.NamedTemporaryFile(
            suffix=suffix,
            delete=False,
            dir='/tmp'  # Explicitly use Lambda's temp directory
        )
        temp_path = temp_file.name
        
        # If we already have a GET response, use it; otherwise make the request
        if response.request.method != 'GET':
            response = requests.get(url, stream=True, allow_redirects=True)
        
        # Stream download
        response.raise_for_status()
        
        downloaded = 0
        with temp_file, tqdm(
            total=total_size,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
            desc=f"Downloading {os.path.basename(parsed.path)}",
            miniters=1
        ) as pbar:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    # Check timeout
                    if time.time() - start_time > MAX_DOWNLOAD_SECONDS:
                        raise TimeoutError(
                            f"Download exceeded {MAX_DOWNLOAD_SECONDS}s Lambda timeout limit"
                        )
                    
                    size = len(chunk)
                    temp_file.write(chunk)
                    downloaded += size
                    pbar.update(size)
        
        logger.info(f"Download completed in {time.time() - start_time:.1f}s")
        return temp_path
    
    except (requests.RequestException, ValueError, TimeoutError) as e:
        logger.error(f"Download failed: {str(e)}", exc_info=True)
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)
        raise
    except Exception as e:
        logger.error(f"Unexpected error during download: {str(e)}", exc_info=True)
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)
        raise 