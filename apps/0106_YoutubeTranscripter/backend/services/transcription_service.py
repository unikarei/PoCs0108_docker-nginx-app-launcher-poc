"""
Transcription Service
Handles audio-to-text conversion using OpenAI Whisper API
"""
from openai import OpenAI
import os
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import logging
import json

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    """
    Result of transcription operation
    """
    success: bool
    text: Optional[str] = None
    language_detected: Optional[str] = None
    model: Optional[str] = None
    duration_seconds: Optional[int] = None
    segments: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None


class TranscriptionService:
    """
    Service for transcribing audio files using OpenAI Whisper API
    """
    
    def _max_upload_bytes(self) -> int:
        # OpenAI upload limit default 25MB (configurable)
        mb = 1024 * 1024
        try:
            return int(os.getenv("MAX_UPLOAD_MB", "25")) * mb
        except ValueError:
            return 25 * mb
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize transcription service
        
        Args:
            api_key: OpenAI API key (uses env var if not provided)
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            logger.warning("OpenAI API key not provided")
            self.client = None
        else:
            try:
                # Initialize with timeout settings
                self.client = OpenAI(
                    api_key=self.api_key,
                    timeout=120.0,  # 2 minutes timeout
                    max_retries=3   # Retry up to 3 times
                )
                logger.info("OpenAI client initialized successfully for transcription")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self.client = None
    
    def transcribe(
        self,
        audio_file_path: str,
        language: Optional[str] = None,
        model: str = "gpt-4o-mini-transcribe",
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio file to text
        
        Args:
            audio_file_path: Path to audio file
            language: Target language code (ja, en, etc)
            model: Whisper model to use
            prompt: Optional prompt hint for better accuracy
            
        Returns:
            Dict with transcription result
        """
        # Check if file exists
        if not os.path.exists(audio_file_path):
            logger.error(f"Audio file not found: {audio_file_path}")
            return {
                'success': False,
                'error': f"Audio file not found: {audio_file_path}"
            }
        
        # Check file size (defensive; large-file handling should preprocess first)
        file_size = os.path.getsize(audio_file_path)
        max_upload_bytes = self._max_upload_bytes()
        if file_size > max_upload_bytes:
            logger.error(f"File size {file_size} exceeds upload limit ({max_upload_bytes})")
            max_mb = max_upload_bytes / 1024 / 1024
            return {
                'success': False,
                'error': (
                    f"File size exceeds upload limit (max: {max_mb:.0f}MB, current: {file_size / 1024 / 1024:.1f}MB)"
                )
            }
        
        if not self.client:
            logger.error("OpenAI client not initialized")
            return {
                'success': False,
                'error': "OpenAI API key not configured"
            }
        
        try:
            # Open audio file
            with open(audio_file_path, 'rb') as audio_file:
                # Prepare API parameters
                api_params = {
                    'model': model,
                    'file': audio_file,
                }
                
                # Add optional parameters
                if language:
                    api_params['language'] = language
                
                if prompt:
                    api_params['prompt'] = prompt

                # Request timestamps when supported
                # NOTE: Some models may reject these parameters; we retry without them.
                api_params_verbose = dict(api_params)
                api_params_verbose['response_format'] = 'verbose_json'

                # NOTE: openai==1.10.0 SDK does not accept timestamp_granularities.
                # verbose_json alone may still include segments when the API/model supports it.

                def _extract_segments(resp: Any) -> Optional[List[Dict[str, Any]]]:
                    raw_segments = None

                    if isinstance(resp, dict):
                        raw_segments = resp.get('segments')
                    else:
                        raw_segments = getattr(resp, 'segments', None)
                        if raw_segments is None and hasattr(resp, 'model_dump'):
                            try:
                                dumped = resp.model_dump()
                                if isinstance(dumped, dict):
                                    raw_segments = dumped.get('segments')
                            except Exception:
                                raw_segments = None

                    if not raw_segments:
                        return None

                    extracted: List[Dict[str, Any]] = []
                    for seg in raw_segments:
                        if isinstance(seg, dict):
                            raw_text = seg.get('text', '')
                            if isinstance(raw_text, (list, tuple)):
                                text = " ".join(str(x) for x in raw_text).strip()
                            else:
                                text = str(raw_text or "").strip()

                            # Some providers/models return a JSON-stringified single-item array like: ["..."]
                            # Unwrap it to improve downstream exports.
                            if text.startswith('["') and text.endswith('"]'):
                                try:
                                    decoded = json.loads(text)
                                    if isinstance(decoded, list) and decoded and all(isinstance(x, str) for x in decoded):
                                        text = " ".join(decoded).strip()
                                except Exception:
                                    pass

                            extracted.append(
                                {
                                    'start': float(seg.get('start', 0.0)),
                                    'end': float(seg.get('end', float(seg.get('start', 0.0)))),
                                    'text': text,
                                }
                            )
                        else:
                            raw_text = getattr(seg, 'text', '')
                            if isinstance(raw_text, (list, tuple)):
                                text = " ".join(str(x) for x in raw_text).strip()
                            else:
                                text = str(raw_text or "").strip()

                            if text.startswith('["') and text.endswith('"]'):
                                try:
                                    decoded = json.loads(text)
                                    if isinstance(decoded, list) and decoded and all(isinstance(x, str) for x in decoded):
                                        text = " ".join(decoded).strip()
                                except Exception:
                                    pass

                            extracted.append(
                                {
                                    'start': float(getattr(seg, 'start', 0.0)),
                                    'end': float(getattr(seg, 'end', getattr(seg, 'start', 0.0))),
                                    'text': text,
                                }
                            )
                    return extracted or None
                
                # Call transcription API
                logger.info(
                    "Transcribing %s with model %s (size_bytes=%s)",
                    audio_file_path,
                    model,
                    file_size,
                )

                try:
                    response = self.client.audio.transcriptions.create(**api_params_verbose)
                    used_timestamps = True
                except Exception as e:
                    logger.warning("Verbose transcription failed; retrying without timestamps: %s", e)
                    response = self.client.audio.transcriptions.create(**api_params)
                    used_timestamps = False
                
                # Extract result
                # Extract segments when available
                segments = _extract_segments(response)

                # If we requested timestamps but got none, do a best-effort retry in verbose_json mode.
                if used_timestamps and not segments:
                    try:
                        response2 = self.client.audio.transcriptions.create(**api_params_verbose)
                        segments = _extract_segments(response2) or segments
                        if segments:
                            response = response2
                    except Exception:
                        pass

                result = {
                    'success': True,
                    'text': response.text,
                    'model': model,
                    'segments': segments,
                }
                
                # Add detected language if available
                if hasattr(response, 'language'):
                    result['language_detected'] = response.language
                
                logger.info(f"Transcription completed: {len(response.text)} characters")
                return result
                
        except FileNotFoundError as e:
            logger.error(f"File not found during transcription: {e}")
            return {
                'success': False,
                'error': f"File not found: {str(e)}"
            }
        
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return {
                'success': False,
                'error': f"Transcription failed: {str(e)}"
            }

    def transcribe_audio(
        self,
        audio_path: str,
        language: Optional[str] = None,
        model: str = "gpt-4o-mini-transcribe",
        prompt: Optional[str] = None
    ) -> TranscriptionResult:
        """Wrapper that returns a typed TranscriptionResult"""
        raw = self.transcribe(
            audio_file_path=audio_path,
            language=language,
            model=model,
            prompt=prompt,
        )

        return TranscriptionResult(
            success=raw.get('success', False),
            text=raw.get('text'),
            language_detected=raw.get('language_detected'),
            model=raw.get('model', model),
            segments=raw.get('segments'),
            error=raw.get('error'),
        )
