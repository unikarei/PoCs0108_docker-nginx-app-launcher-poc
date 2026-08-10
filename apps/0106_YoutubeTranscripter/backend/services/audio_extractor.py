"""
Audio Extractor Service
Handles YouTube audio extraction using yt-dlp
"""
import yt_dlp
import os
import re
import shutil
from dataclasses import dataclass
from typing import Optional, Dict, Any, Callable, List
from pathlib import Path
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class ProgressCallback:
    """
    Progress callback for yt-dlp downloads
    Updates job progress in database
    """

    def __init__(self, job_id: str):
        self.job_id = job_id
        self.job_manager = None
        try:
            from services.job_manager import JobManager
            self.job_manager = JobManager()
        except ImportError:
            logger.warning("JobManager not available for progress updates")

    def hook(self, d: Dict[str, Any]):
        if not self.job_manager:
            return
        try:
            status = d.get('status')
            if status == 'downloading':
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                if total > 0:
                    progress = int((downloaded / total) * 100)
                    progress = min(progress * 0.9, 90)
                    self.job_manager.update_job_progress(self.job_id, int(progress))
            elif status == 'finished':
                self.job_manager.update_job_progress(self.job_id, 95, "Processing audio")
                logger.info(f"Download finished for job {self.job_id}")
            elif status == 'error':
                logger.error(f"Download error for job {self.job_id}")
        except Exception as e:
            logger.debug("Progress callback error (non-fatal): %s", e)


@dataclass
class AudioExtractionResult:
    """Result of audio extraction operation"""
    success: bool
    file_path: Optional[str]
    duration_seconds: Optional[int]
    title: Optional[str]
    error: Optional[str]
    file_size_bytes: Optional[int] = None
    format: Optional[str] = None

    @property
    def audio_path(self) -> Optional[str]:
        """Backward-compatible alias for older code."""
        return self.file_path

    @audio_path.setter
    def audio_path(self, value: Optional[str]) -> None:
        self.file_path = value


class AudioExtractor:
    """
    Service for extracting audio from YouTube videos
    """

    # Maximum video duration in seconds (0 = no limit)
    MAX_DURATION_SECONDS = int(os.getenv('MAX_VIDEO_DURATION_SECONDS', '0'))

    YOUTUBE_PATTERNS = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+(?:[&?].*)?$',
        r'(?:https?://)?(?:www\.)?youtu\.be/[\w-]+(?:[?].*)?$',
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/[\w-]+(?:[?].*)?$',
        r'(?:https?://)?(?:www\.)?youtube\.com/shorts/[\w-]+(?:[?].*)?$',
    ]

    ANSI_ESCAPE_PATTERN = re.compile(r'\x1b\[[0-9;]*m')

    def __init__(self, output_dir: str = "audio_files"):
        self.output_dir = output_dir
        self.audio_dir = output_dir
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

        # Check ffmpeg availability at init time
        self._ffmpeg_available = shutil.which("ffmpeg") is not None
        if not self._ffmpeg_available:
            logger.warning("ffmpeg not available; audio post-processing will be skipped")

    def _get_download_strategies(self) -> List[Dict[str, Any]]:
        """Build ordered download strategies based on environment capabilities."""
        strategies: List[Dict[str, Any]] = []

        if self._ffmpeg_available:
            strategies.append({
                "name": "preferred_audio",
                "expected_ext": "m4a",
                "options": {
                    'format': 'bestaudio[ext=m4a]/bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'm4a',
                        'preferredquality': '192',
                    }],
                    'extract_audio': True,
                },
            })
        else:
            # Without ffmpeg, download best audio in its native container
            strategies.append({
                "name": "preferred_audio_no_ffmpeg",
                "expected_ext": None,
                "options": {
                    'format': 'bestaudio/best',
                },
            })

        # Fallback: android progressive (format 18 = mp4 360p a+v)
        strategies.append({
            "name": "android_progressive_fallback",
            "expected_ext": "mp4",
            "options": {
                'format': '18/best[ext=mp4]/best',
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android'],
                    }
                },
            },
        })

        return strategies

    # ── helpers ──

    def _normalize_error_message(self, error: Optional[str]) -> str:
        """Strip ANSI escape sequences from yt-dlp error messages."""
        return self.ANSI_ESCAPE_PATTERN.sub('', error or '').strip()

    def _cleanup_temporary_files(self, job_id: str) -> None:
        """Remove leftover partial files between retry strategies."""
        output_dir = Path(self.output_dir)
        for path in output_dir.glob(f"{job_id}*"):
            if not path.is_file():
                continue
            suffixes = ''.join(path.suffixes)
            if suffixes.endswith('.part') or suffixes.endswith('.ytdl') or path.suffix == '.temp':
                try:
                    path.unlink()
                except OSError:
                    logger.debug("Failed to remove temporary file: %s", path)

    def _resolve_downloaded_file_path(
        self,
        job_id: str,
        info: Optional[Dict[str, Any]],
        expected_ext: Optional[str],
    ) -> str:
        """Find the concrete downloaded file path after yt-dlp finishes."""
        output_dir = Path(self.output_dir)
        candidates: List[Path] = []
        for path in output_dir.glob(f"{job_id}.*"):
            if not path.is_file():
                continue
            if any(str(path).endswith(ext) for ext in ('.part', '.ytdl', '.temp')):
                continue
            candidates.append(path)

        preferred_exts: List[str] = []
        if expected_ext:
            preferred_exts.append(expected_ext)
        info_ext = (info or {}).get('ext')
        if info_ext and info_ext not in preferred_exts:
            preferred_exts.append(info_ext)

        for ext in preferred_exts:
            for candidate in candidates:
                if candidate.suffix.lower() == f'.{ext.lower()}':
                    return str(candidate)

        if candidates:
            candidates.sort(key=lambda item: item.suffix)
            return str(candidates[0])

        fallback_ext = preferred_exts[0] if preferred_exts else 'm4a'
        return os.path.join(self.output_dir, f"{job_id}.{fallback_ext}")

    def _build_ydl_opts(
        self,
        output_path: str,
        progress_hook: Callable[[Dict[str, Any]], None],
        strategy: Dict[str, Any],
    ) -> Dict[str, Any]:
        opts: Dict[str, Any] = {
            'format': 'bestaudio/best',
            'outtmpl': output_path,
            'quiet': False,
            'no_warnings': False,
            'progress_hooks': [progress_hook],
            'noplaylist': True,
        }
        opts.update(strategy.get('options', {}))
        return opts

    # ── public API ──

    def validate_youtube_url(self, url: str) -> bool:
        if not url or not isinstance(url, str):
            return False
        for pattern in self.YOUTUBE_PATTERNS:
            if re.match(pattern, url):
                return True
        return False

    def get_video_info(self, youtube_url: str) -> Optional[Dict[str, Any]]:
        """Get video information without downloading."""
        attempts = [
            {'quiet': True, 'no_warnings': True, 'extract_flat': False},
            {
                'quiet': True, 'no_warnings': True, 'extract_flat': False,
                'extractor_args': {'youtube': {'player_client': ['android']}},
            },
        ]
        for attempt in attempts:
            try:
                with yt_dlp.YoutubeDL(attempt) as ydl:
                    info = ydl.extract_info(youtube_url, download=False)
                    if info:
                        return info
            except Exception as e:
                logger.warning("Failed to get video info: %s", e)
        return None

    def extract_audio(self, youtube_url: str, job_id: str) -> AudioExtractionResult:
        """
        Extract audio from YouTube video.

        Tries multiple download strategies in order, falling back to the next
        when YouTube returns HTTP 403 or another transient error.
        """
        # Validate URL
        if not self.validate_youtube_url(youtube_url):
            return AudioExtractionResult(
                success=False, file_path=None, duration_seconds=None,
                title=None, error="Invalid YouTube URL format",
            )

        # Fetch metadata upfront (title, duration) for early checks
        try:
            video_info = self.get_video_info(youtube_url)
        except Exception as e:
            logger.warning('Failed to fetch video metadata: %s', e)
            return AudioExtractionResult(
                success=False, file_path=None,
                duration_seconds=None, title=None,
                error=f'Extraction failed: {self._normalize_error_message(str(e))}',
            )
        title = video_info.get('title') if video_info else None
        duration = video_info.get('duration', 0) if video_info else None

        # Check duration limit
        if self.MAX_DURATION_SECONDS > 0 and duration and duration > self.MAX_DURATION_SECONDS:
            limit_minutes = self.MAX_DURATION_SECONDS // 60
            return AudioExtractionResult(
                success=False, file_path=None,
                duration_seconds=duration, title=title,
                error=f"Video duration exceeds {limit_minutes} minute limit ({duration}s)",
            )

        output_path = os.path.join(self.output_dir, f"{job_id}.%(ext)s")
        progress_callback = ProgressCallback(job_id)
        strategies = self._get_download_strategies()

        try:
            last_error: Optional[str] = None

            for strategy in strategies:
                strategy_name = strategy.get('name', 'unknown')
                ydl_opts = self._build_ydl_opts(output_path, progress_callback.hook, strategy)
                self._cleanup_temporary_files(job_id)

                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        logger.info("Downloading audio for %s with strategy=%s", youtube_url, strategy_name)
                        dl_info = ydl.extract_info(youtube_url, download=True)

                        # Update metadata from download result if we didn't get it before
                        if dl_info:
                            title = dl_info.get('title') or title
                            duration = dl_info.get('duration', 0) or duration

                        final_path = self._resolve_downloaded_file_path(
                            job_id=job_id, info=dl_info, expected_ext=strategy.get('expected_ext'),
                        )

                        file_size = None
                        try:
                            file_size = os.path.getsize(final_path)
                        except OSError:
                            file_size = None

                        final_format = Path(final_path).suffix.lstrip('.') or strategy.get('expected_ext')

                        return AudioExtractionResult(
                            success=True, file_path=final_path,
                            duration_seconds=duration, title=title,
                            error=None, file_size_bytes=file_size,
                            format=final_format,
                        )

                except yt_dlp.DownloadError as e:
                    last_error = self._normalize_error_message(str(e))
                    logger.warning("Strategy %s failed for %s: %s", strategy_name, youtube_url, last_error)
                    continue
                except Exception as e:
                    last_error = self._normalize_error_message(str(e))
                    logger.warning("Strategy %s unexpected failure for %s: %s", strategy_name, youtube_url, last_error)
                    continue

            # All strategies exhausted
            return AudioExtractionResult(
                success=False, file_path=None,
                duration_seconds=duration, title=title,
                error=last_error or "Extraction failed",
            )

        except Exception as e:
            cleaned = self._normalize_error_message(str(e))
            logger.error(f"Unexpected error extracting audio: {cleaned}")
            return AudioExtractionResult(
                success=False, file_path=None,
                duration_seconds=None, title=None,
                error=f"Extraction failed: {cleaned}",
            )
