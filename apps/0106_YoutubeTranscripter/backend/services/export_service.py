"""
Export Service
Handles exporting transcripts to various formats (TXT, SRT, VTT)
"""
import logging
import re
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class ExportResult:
    """
    Result of export operation
    """
    success: bool
    format: str
    content: Optional[str] = None
    filename: Optional[str] = None
    error: Optional[str] = None


class ExportService:
    """
    Service for exporting transcripts to various formats
    """
    
    def __init__(self):
        """Initialize export service"""
        pass
    
    def export_to_txt(self, transcript: str) -> str:
        """
        Export transcript to plain text format
        
        Args:
            transcript: Transcript text
            
        Returns:
            Plain text content
        """
        if not transcript:
            return ""
        
        # Plain text - just return as-is
        logger.info("Exported transcript to TXT format")
        return transcript
    
    def export_to_srt(
        self,
        transcript: str,
        duration_seconds: int,
        segments: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Export transcript to SRT subtitle format
        
        Args:
            transcript: Transcript text
            duration_seconds: Total audio duration
            
        Returns:
            SRT formatted content
        """
        if not transcript:
            return ""
        
        # Prefer timestamped segments when provided
        if segments:
            segments = list(segments)
        else:
            segments = self._split_into_segments(transcript, duration_seconds)
        
        # Build SRT format
        srt_lines = []
        
        for i, segment in enumerate(segments, start=1):
            # Sequence number
            srt_lines.append(str(i))
            
            # Timestamps
            start_time = self._format_srt_timestamp(float(segment.get('start', 0.0)))
            end_time = self._format_srt_timestamp(float(segment.get('end', 0.0)))
            srt_lines.append(f"{start_time} --> {end_time}")
            
            # Text
            srt_lines.append((segment.get('text') or '').strip())
            
            # Blank line separator
            srt_lines.append("")
        
        logger.info(f"Exported transcript to SRT format ({len(segments)} segments)")
        return "\n".join(srt_lines)
    
    def export_to_vtt(
        self,
        transcript: str,
        duration_seconds: int,
        segments: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Export transcript to WebVTT format
        
        Args:
            transcript: Transcript text
            duration_seconds: Total audio duration
            
        Returns:
            WebVTT formatted content
        """
        if not transcript:
            return "WEBVTT\n\n"
        
        # Prefer timestamped segments when provided
        if segments:
            segments = list(segments)
        else:
            segments = self._split_into_segments(transcript, duration_seconds)
        
        # Build VTT format
        vtt_lines = ["WEBVTT", ""]
        
        for segment in segments:
            # Timestamps
            start_time = self._format_vtt_timestamp(float(segment.get('start', 0.0)))
            end_time = self._format_vtt_timestamp(float(segment.get('end', 0.0)))
            vtt_lines.append(f"{start_time} --> {end_time}")
            
            # Text
            vtt_lines.append((segment.get('text') or '').strip())
            
            # Blank line separator
            vtt_lines.append("")
        
        logger.info(f"Exported transcript to VTT format ({len(segments)} segments)")
        return "\n".join(vtt_lines)
    
    def _split_into_segments(self, transcript: str, duration_seconds: int) -> List[Dict[str, Any]]:
        """
        Split transcript into timed segments
        
        Args:
            transcript: Transcript text
            duration_seconds: Total duration
            
        Returns:
            List of segments with text, start, and end times
        """
        # Split by sentence endings
        sentences = re.split(r'([。．！？\.\!\?])', transcript)
        
        # Reconstruct sentences with punctuation
        segments = []
        current_sentence = ""
        
        for i, part in enumerate(sentences):
            current_sentence += part
            
            # If this is punctuation and not the last item, save sentence
            if i % 2 == 1 and current_sentence.strip():
                segments.append({'text': current_sentence.strip()})
                current_sentence = ""
        
        # Add remaining text
        if current_sentence.strip():
            segments.append({'text': current_sentence.strip()})
        
        # If no segments, return whole text
        if not segments:
            segments = [{'text': transcript}]
        
        # Distribute timestamps evenly
        segments = self._distribute_timestamps(segments, duration_seconds)
        
        return segments
    
    def _distribute_timestamps(
        self,
        segments: List[Dict[str, str]],
        duration_seconds: int
    ) -> List[Dict[str, Any]]:
        """
        Distribute timestamps evenly across segments
        
        Args:
            segments: List of text segments
            duration_seconds: Total duration
            
        Returns:
            Segments with start and end times
        """
        if not segments:
            return []
        
        num_segments = len(segments)
        time_per_segment = duration_seconds / num_segments
        
        for i, segment in enumerate(segments):
            segment['start'] = i * time_per_segment
            segment['end'] = (i + 1) * time_per_segment
        
        return segments
    
    def _format_srt_timestamp(self, seconds: float) -> str:
        """
        Format timestamp for SRT format (HH:MM:SS,mmm)
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted timestamp
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def _format_vtt_timestamp(self, seconds: float) -> str:
        """
        Format timestamp for VTT format (HH:MM:SS.mmm)
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted timestamp
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
    
    def validate_srt_format(self, content: str) -> bool:
        """
        Validate SRT format
        
        Args:
            content: SRT content to validate
            
        Returns:
            True if valid
        """
        try:
            # Check for sequence numbers
            if not re.search(r'^\d+$', content, re.MULTILINE):
                return False
            
            # Check for timestamp format
            if not re.search(r'\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}', content):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"SRT validation error: {e}")
            return False
    
    def validate_vtt_format(self, content: str) -> bool:
        """
        Validate VTT format
        
        Args:
            content: VTT content to validate
            
        Returns:
            True if valid
        """
        try:
            # Check for WEBVTT header
            if not content.startswith("WEBVTT"):
                return False
            
            # Check for timestamp format
            if not re.search(r'\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}', content):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"VTT validation error: {e}")
            return False
