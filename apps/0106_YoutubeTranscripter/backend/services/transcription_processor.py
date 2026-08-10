"""
Transcription Result Processing and Validation
Handles post-processing, language detection, database storage
"""
import re
import logging
from typing import Optional, Dict, Any, Tuple
from langdetect import detect, LangDetectException

from database import SessionLocal
from models import Transcript

logger = logging.getLogger(__name__)


class TranscriptionProcessor:
    """
    Service for processing and validating transcription results
    """
    
    def __init__(self):
        """Initialize transcription processor"""
        self.job_manager = None
        
        # Lazy import to avoid circular dependency
        try:
            from services.job_manager import JobManager
            self.job_manager = JobManager()
        except ImportError:
            logger.warning("JobManager not available")
    
    def process_transcript(self, raw_text: str) -> str:
        """
        Process raw transcript text (add punctuation, paragraphs)
        
        Args:
            raw_text: Raw transcription text
            
        Returns:
            Processed text with better formatting
        """
        if not raw_text:
            return ""
        
        # Basic processing - in production, this could use NLP libraries
        # For now, just return the text as-is since Whisper already adds punctuation
        processed = raw_text.strip()
        
        # Add paragraph breaks for very long text (every ~5 sentences)
        sentences = re.split(r'([。．！？\.\!\?])', processed)
        
        # Reconstruct with paragraph breaks
        result = []
        current_paragraph = []
        
        for i in range(0, len(sentences), 2):
            if i < len(sentences):
                sentence = sentences[i]
                punctuation = sentences[i + 1] if i + 1 < len(sentences) else ""
                
                current_paragraph.append(sentence + punctuation)
                
                # Add paragraph break every 5 sentences
                if len(current_paragraph) >= 5:
                    result.append(''.join(current_paragraph).strip())
                    current_paragraph = []
        
        # Add remaining sentences
        if current_paragraph:
            result.append(''.join(current_paragraph).strip())
        
        return '\n\n'.join(result) if result else processed
    
    def detect_language(self, text: str) -> str:
        """
        Detect language of text
        
        Args:
            text: Text to analyze
            
        Returns:
            Language code (ja, en, etc.)
        """
        try:
            detected = detect(text)
            logger.debug(f"Detected language: {detected}")
            return detected
        except LangDetectException as e:
            logger.warning(f"Language detection failed: {e}")
            return "unknown"
    
    def validate_language(self, text: str, expected_language: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that detected language matches expected
        
        Args:
            text: Transcript text
            expected_language: Expected language code
            
        Returns:
            Tuple of (is_valid, warning_message)
        """
        detected = self.detect_language(text)
        
        if detected == "unknown":
            return True, "Could not detect language"
        
        if detected != expected_language:
            warning = (
                f"Language mismatch: expected '{expected_language}', "
                f"detected '{detected}'"
            )
            logger.warning(warning)
            return False, warning
        
        return True, None
    
    def save_transcript(
        self,
        job_id: str,
        text: str,
        language_detected: str,
        model: str
    ) -> bool:
        """
        Save transcript to database
        
        Args:
            job_id: Job identifier
            text: Transcription text
            language_detected: Detected language
            model: Model used for transcription
            
        Returns:
            True if successful, False otherwise
        """
        db = SessionLocal()
        try:
            transcript = Transcript(
                job_id=job_id,
                text=text,
                language_detected=language_detected,
                transcription_model=model
            )
            
            db.add(transcript)
            db.commit()
            
            logger.info(f"Saved transcript for job {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save transcript: {e}")
            db.rollback()
            return False
            
        finally:
            db.close()
    
    def calculate_estimated_time(
        self,
        audio_duration_seconds: int,
        current_progress: int
    ) -> float:
        """
        Calculate estimated remaining time
        
        Args:
            audio_duration_seconds: Total audio duration
            current_progress: Current progress (0-100)
            
        Returns:
            Estimated seconds remaining
        """
        if current_progress >= 100:
            return 0
        
        if current_progress <= 0:
            # Rough estimate: transcription takes ~20% of audio duration
            return audio_duration_seconds * 0.2
        
        # Calculate based on current progress
        # Assume transcription time is proportional to audio duration
        transcription_rate = 0.2  # 20% of audio duration
        total_estimated = audio_duration_seconds * transcription_rate
        remaining = total_estimated * (100 - current_progress) / 100
        
        return remaining
    
    def update_progress(
        self,
        job_id: str,
        progress: int,
        audio_duration: Optional[int] = None
    ):
        """
        Update job progress with time estimation
        
        Args:
            job_id: Job identifier
            progress: Progress percentage (0-100)
            audio_duration: Optional audio duration for time estimation
        """
        if not self.job_manager:
            logger.warning("JobManager not available for progress update")
            return
        
        # Calculate estimated time if duration provided
        message = None
        if audio_duration and progress < 100:
            estimated_seconds = self.calculate_estimated_time(audio_duration, progress)
            estimated_minutes = int(estimated_seconds / 60)
            message = f"Estimated time remaining: {estimated_minutes} minutes"
        
        self.job_manager.update_job_progress(job_id, progress, message)
    
    def post_process(
        self,
        transcript_text: str,
        expected_language: str,
        job_id: str,
        model: str
    ) -> Dict[str, Any]:
        """
        Complete post-processing workflow
        
        Args:
            transcript_text: Raw transcript text
            expected_language: Expected language
            job_id: Job identifier
            model: Model used
            
        Returns:
            Dict with processed result and metadata
        """
        # Process text
        processed_text = self.process_transcript(transcript_text)
        
        # Validate language
        language_valid, warning = self.validate_language(processed_text, expected_language)
        
        # Detect language
        detected_language = self.detect_language(processed_text)
        
        # Save to database
        saved = self.save_transcript(
            job_id=job_id,
            text=processed_text,
            language_detected=detected_language,
            model=model
        )
        
        result = {
            'text': processed_text,
            'language_detected': detected_language,
            'language_valid': language_valid,
            'warning': warning,
            'saved': saved
        }
        
        logger.info(f"Post-processing complete for job {job_id}")
        return result
