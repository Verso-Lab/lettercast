import os
import logging
import time
from pathlib import Path
from pydub import AudioSegment
import tempfile

logger = logging.getLogger(__name__)

def transform_audio(audio_path):
    """Transform audio to reduce file size and optimize for Gemini API"""
    try:
        start_time = time.time()
        logger.info(f"Starting audio transformation for: {audio_path}")
        
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Get original file size
        original_size = os.path.getsize(audio_path) / (1024 * 1024)
        logger.info(f"Original file size: {original_size:.2f} MB")
        
        try:
            # Load audio file
            logger.info("Loading audio file...")
            audio = AudioSegment.from_file(audio_path)
        except Exception as e:
            raise Exception(f"Failed to load audio file: {str(e)}")
        
        logger.info(f"Original audio: {audio.channels} channels, {audio.frame_rate}Hz")
        
        try:
            # Convert to mono
            audio = audio.set_channels(1)
            logger.info("Converted to mono")
            
            # Reduce sample rate to 16kHz
            audio = audio.set_frame_rate(16000)
            logger.info("Reduced sample rate to 16kHz")
        except Exception as e:
            raise Exception(f"Failed to process audio: {str(e)}")
        
        try:
            # Export with reduced quality
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_file:
                logger.info("Exporting compressed audio...")
                audio.export(tmp_file.name, format='mp3', 
                           parameters=["-q:a", "9"])
                
                compressed_size = os.path.getsize(tmp_file.name) / (1024 * 1024)
                reduction = ((original_size - compressed_size) / original_size) * 100
                
                logger.info(f"Compressed file size: {compressed_size:.2f} MB")
                logger.info(f"Size reduction: {reduction:.1f}%")
                logger.info(f"Transformation completed in {time.time() - start_time:.1f} seconds")
                
                return tmp_file.name
        except Exception as e:
            raise Exception(f"Failed to export compressed audio: {str(e)}")
        
    except Exception as e:
        logger.error(f"Error in transform_audio: {str(e)}", exc_info=True)
        raise 