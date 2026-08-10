"""Audio preprocessing for large files.

OpenAI audio upload has a per-request size limit. This module ensures extracted audio is
safe to upload by applying speech-friendly compression and (if needed) splitting into
chunks with overlap.

Design goals:
- Minimal disruption to existing pipeline
- Cross-platform (Windows/WSL2/Linux) via ffmpeg executable
- Deterministic planning using a target upload size (safety margin)
"""

from __future__ import annotations

import json
import logging
import math
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Literal, Optional

logger = logging.getLogger(__name__)


MB = 1024 * 1024


def _get_env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid %s=%r; using default=%s", name, raw, default)
        return default


def _get_env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning("Invalid %s=%r; using default=%s", name, raw, default)
        return default


@dataclass
class Chunk:
    path: str
    index: int
    start_offset_sec: float
    duration_sec: float
    size_bytes: int


@dataclass
class PreprocessPlan:
    strategy: Literal["as_is", "compress", "compress_then_split"]
    input_size_bytes: int
    target_upload_bytes: int
    chunk_overlap_sec: float
    chunks: List[Chunk]


@dataclass
class PreprocessResult:
    success: bool
    plan: Optional[PreprocessPlan] = None
    error: Optional[str] = None


def estimate_bytes_per_second(audio_bitrate_kbps: int) -> float:
    # bitrate_kbps * 1000 bits/sec -> /8 bytes/sec
    return (audio_bitrate_kbps * 1000) / 8.0


def plan_chunk_duration_seconds(
    target_upload_bytes: int,
    audio_bitrate_kbps: int,
    chunk_overlap_sec: float,
    safety_factor: float = 0.95,
    min_chunk_sec: int = 30,
) -> int:
    """Plan nominal chunk duration (without leading overlap).

    We only add leading overlap to all chunks after the first. To keep each chunk
    comfortably under the target, we budget overlap into the size estimate.
    """

    if target_upload_bytes <= 0:
        raise ValueError("target_upload_bytes must be positive")

    if audio_bitrate_kbps <= 0:
        raise ValueError("audio_bitrate_kbps must be positive")

    bytes_per_sec = estimate_bytes_per_second(audio_bitrate_kbps)

    # Budget for leading overlap. Worst-case chunk size occurs for chunks after the first.
    max_allowed_duration = (target_upload_bytes * safety_factor) / bytes_per_sec
    nominal = max_allowed_duration - float(chunk_overlap_sec)

    if nominal < float(min_chunk_sec):
        return min_chunk_sec

    return int(math.floor(nominal))


def plan_nominal_chunk_seconds_for_max_duration(
    max_total_duration_sec: float,
    chunk_overlap_sec: float,
    safety_factor: float = 0.98,
    min_chunk_sec: int = 30,
) -> int:
    """Plan nominal chunk duration based on a model's max audio duration.

    The worst-case chunk duration occurs for chunks after the first because we add
    a leading overlap. To keep every request under the model limit, we plan:

      worst_case_duration ~= nominal + overlap <= max_total_duration_sec * safety_factor

    We keep a small safety margin to avoid boundary/metadata rounding issues.
    """

    if max_total_duration_sec <= 0:
        raise ValueError("max_total_duration_sec must be positive")

    if chunk_overlap_sec < 0:
        raise ValueError("chunk_overlap_sec must be non-negative")

    budget = (float(max_total_duration_sec) * float(safety_factor)) - float(chunk_overlap_sec)
    nominal = int(math.floor(budget))
    return max(int(min_chunk_sec), nominal)


class AudioPreprocessor:
    def __init__(self, work_root: str = "audio_files"):
        self.work_root = Path(work_root)
        self.work_root.mkdir(parents=True, exist_ok=True)

        self.max_upload_mb = _get_env_int("MAX_UPLOAD_MB", 25)
        self.target_upload_mb = _get_env_int("TARGET_UPLOAD_MB", 24)
        self.chunk_overlap_sec = _get_env_float("CHUNK_OVERLAP_SEC", 0.8)
        # Some providers/models can truncate long single-shot transcriptions.
        # To improve reliability, we can force splitting when audio duration exceeds this.
        # Set <=0 to disable.
        self.max_single_chunk_sec = _get_env_int("MAX_SINGLE_CHUNK_SEC", 900)
        # Reasonable speech bitrate default
        self.audio_bitrate_kbps = _get_env_int("AUDIO_BITRATE_KBPS", 48)

    def _ensure_ffmpeg(self) -> Optional[str]:
        return shutil.which("ffmpeg")

    def _job_dir(self, job_id: str) -> Path:
        path = self.work_root / job_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _run_ffmpeg(self, args: List[str]) -> subprocess.CompletedProcess:
        ffmpeg = self._ensure_ffmpeg()
        if not ffmpeg:
            raise RuntimeError("ffmpeg not found in PATH")

        cmd = [ffmpeg, "-y"] + args
        logger.debug("Running ffmpeg: %s", " ".join(cmd))
        return subprocess.run(cmd, capture_output=True, text=True)

    def _compress_to_speech_mp3(self, input_path: str, output_path: str) -> None:
        # Speech-friendly: mono + 16kHz + stable bitrate
        result = self._run_ffmpeg(
            [
                "-i",
                input_path,
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-b:a",
                f"{self.audio_bitrate_kbps}k",
                output_path,
            ]
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"ffmpeg compression failed: {result.stderr.strip() or result.stdout.strip()}"
            )

    def _split_mp3_into_chunks(
        self,
        input_path: str,
        job_dir: Path,
        nominal_chunk_sec: int,
        overlap_sec: float,
    ) -> List[Chunk]:
        # Determine total duration using ffprobe via ffmpeg (fallback):
        # We avoid adding ffprobe dependency explicitly and use ffmpeg -i parse.
        duration = self._probe_duration_seconds(input_path)
        if duration is None:
            raise RuntimeError("Failed to determine audio duration")

        chunks: List[Chunk] = []
        index = 0
        t = 0.0

        while t < duration - 1e-6:
            nominal_start = t
            actual_start = max(0.0, nominal_start - overlap_sec) if index > 0 else 0.0

            remaining = max(0.0, duration - actual_start)
            # include only leading overlap (for index>0). The nominal duration remains nominal_chunk_sec.
            desired = float(nominal_chunk_sec)
            if index == 0:
                actual_duration = min(desired, remaining)
            else:
                actual_duration = min(desired + overlap_sec, remaining)

            out_path = str(job_dir / f"chunk_{index:04d}.mp3")

            # -ss before -i for speed. Use re-encode to avoid inaccurate cuts with mp3.
            result = self._run_ffmpeg(
                [
                    "-ss",
                    f"{actual_start}",
                    "-i",
                    input_path,
                    "-t",
                    f"{actual_duration}",
                    "-vn",
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-b:a",
                    f"{self.audio_bitrate_kbps}k",
                    out_path,
                ]
            )

            if result.returncode != 0:
                raise RuntimeError(
                    f"ffmpeg split failed (chunk {index}): {result.stderr.strip() or result.stdout.strip()}"
                )

            size_bytes = os.path.getsize(out_path)

            chunks.append(
                Chunk(
                    path=out_path,
                    index=index,
                    start_offset_sec=float(actual_start),
                    duration_sec=float(actual_duration),
                    size_bytes=int(size_bytes),
                )
            )

            index += 1
            t += float(nominal_chunk_sec)

        return chunks

    def _probe_duration_seconds(self, input_path: str) -> Optional[float]:
        # Use ffmpeg -i output parsing. This is not perfect, but avoids extra tools.
        ffmpeg = self._ensure_ffmpeg()
        if not ffmpeg:
            return None

        proc = subprocess.run([ffmpeg, "-i", input_path], capture_output=True, text=True)
        text = proc.stderr or proc.stdout or ""

        # Example: Duration: 00:12:34.56,
        import re

        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", text)
        if not m:
            return None

        hours = int(m.group(1))
        minutes = int(m.group(2))
        seconds = float(m.group(3))
        return hours * 3600 + minutes * 60 + seconds

    def _model_max_duration_seconds(self, model: Optional[str]) -> Optional[int]:
        """Return per-request max audio duration for a given transcription model.

        Some OpenAI transcription models enforce a max audio duration per request.
        This preprocessor uses conservative defaults and allows env overrides.
        """

        if not model:
            return None

        # Env override: MAX_AUDIO_DURATION_<MODEL>_SEC
        # e.g. MAX_AUDIO_DURATION_GPT_4O_MINI_TRANSCRIBE_SEC=1400
        key = f"MAX_AUDIO_DURATION_{model.upper().replace('-', '_')}_SEC"
        raw = os.getenv(key)
        if raw:
            try:
                return int(raw)
            except ValueError:
                logger.warning("Invalid %s=%r; ignoring", key, raw)

        # Conservative defaults from observed API errors.
        if model == "gpt-4o-mini-transcribe":
            return 1400

        return None

    def prepare_for_upload(
        self,
        audio_file_path: str,
        job_id: str,
        model: Optional[str] = None,
        duration_seconds: Optional[float] = None,
    ) -> PreprocessResult:
        if not os.path.exists(audio_file_path):
            return PreprocessResult(success=False, error=f"Audio file not found: {audio_file_path}")

        ffmpeg = self._ensure_ffmpeg()
        if not ffmpeg:
            return PreprocessResult(success=False, error="ffmpeg not found in PATH")

        input_size = os.path.getsize(audio_file_path)
        max_upload_bytes = self.max_upload_mb * MB
        target_upload_bytes = self.target_upload_mb * MB

        # Log structured-ish JSON for observability
        logger.info(
            "audio_preprocess_start %s",
            json.dumps(
                {
                    "job_id": job_id,
                    "input_path": audio_file_path,
                    "model": model,
                    "duration_seconds": duration_seconds,
                    "max_single_chunk_sec": self.max_single_chunk_sec,
                    "input_size_bytes": input_size,
                    "max_upload_bytes": max_upload_bytes,
                    "target_upload_bytes": target_upload_bytes,
                    "chunk_overlap_sec": self.chunk_overlap_sec,
                    "audio_bitrate_kbps": self.audio_bitrate_kbps,
                },
                ensure_ascii=False,
            ),
        )

        model_max_sec = self._model_max_duration_seconds(model)

        # Apply an additional global max duration per request (reliability guard).
        duration_limit_sec: Optional[int] = model_max_sec
        if int(self.max_single_chunk_sec) > 0:
            duration_limit_sec = (
                min(int(duration_limit_sec), int(self.max_single_chunk_sec))
                if duration_limit_sec is not None
                else int(self.max_single_chunk_sec)
            )

        effective_duration = float(duration_seconds) if duration_seconds is not None else None
        if effective_duration is None and duration_limit_sec is not None:
            # Only probe if we need duration for decision-making.
            effective_duration = self._probe_duration_seconds(audio_file_path)

        force_split_by_duration = (
            duration_limit_sec is not None
            and effective_duration is not None
            and effective_duration > float(duration_limit_sec)
        )

        if input_size <= max_upload_bytes and not force_split_by_duration:
            plan = PreprocessPlan(
                strategy="as_is",
                input_size_bytes=input_size,
                target_upload_bytes=target_upload_bytes,
                chunk_overlap_sec=self.chunk_overlap_sec,
                chunks=[
                    Chunk(
                        path=audio_file_path,
                        index=0,
                        start_offset_sec=0.0,
                        duration_sec=float(effective_duration or 0.0),
                        size_bytes=input_size,
                    )
                ],
            )
            return PreprocessResult(success=True, plan=plan)

        job_dir = self._job_dir(job_id)

        compressed_path = str(job_dir / "compressed.mp3")
        try:
            # We always compress when we had to touch the audio (size overflow) or
            # when we need duration-based splitting, to ensure deterministic bitrate.
            self._compress_to_speech_mp3(audio_file_path, compressed_path)
        except Exception as e:
            return PreprocessResult(success=False, error=str(e))

        compressed_size = os.path.getsize(compressed_path)

        # If we only needed compression (size reasons) and the result is comfortably small,
        # keep as a single chunk.
        if (
            not force_split_by_duration
            and compressed_size <= max_upload_bytes
            and compressed_size <= target_upload_bytes
        ):
            plan = PreprocessPlan(
                strategy="compress",
                input_size_bytes=input_size,
                target_upload_bytes=target_upload_bytes,
                chunk_overlap_sec=self.chunk_overlap_sec,
                chunks=[
                    Chunk(
                        path=compressed_path,
                        index=0,
                        start_offset_sec=0.0,
                        duration_sec=float(effective_duration or 0.0),
                        size_bytes=compressed_size,
                    )
                ],
            )

            logger.info(
                "audio_preprocess_decision %s",
                json.dumps(
                    {
                        "job_id": job_id,
                        "strategy": plan.strategy,
                        "chunk_count": 1,
                        "chunk_sizes": [compressed_size],
                    },
                    ensure_ascii=False,
                ),
            )
            return PreprocessResult(success=True, plan=plan)

        try:
            nominal_chunk_sec = plan_chunk_duration_seconds(
                target_upload_bytes=target_upload_bytes,
                audio_bitrate_kbps=self.audio_bitrate_kbps,
                chunk_overlap_sec=self.chunk_overlap_sec,
            )

            # Also respect per-request duration limits when known.
            if duration_limit_sec is not None:
                nominal_by_model = plan_nominal_chunk_seconds_for_max_duration(
                    max_total_duration_sec=float(duration_limit_sec),
                    chunk_overlap_sec=self.chunk_overlap_sec,
                )
                nominal_chunk_sec = min(int(nominal_chunk_sec), int(nominal_by_model))

            chunks = self._split_mp3_into_chunks(
                input_path=compressed_path,
                job_dir=job_dir,
                nominal_chunk_sec=nominal_chunk_sec,
                overlap_sec=self.chunk_overlap_sec,
            )

            # Ensure safety: all chunks should be < target_upload_bytes
            oversized = [c for c in chunks if c.size_bytes >= target_upload_bytes]
            if oversized:
                # Provide actionable detail
                details = {
                    "job_id": job_id,
                    "reason": "chunk_size_exceeds_target",
                    "target_upload_bytes": target_upload_bytes,
                    "chunks": [
                        {
                            "index": c.index,
                            "size_bytes": c.size_bytes,
                            "path": c.path,
                        }
                        for c in oversized
                    ],
                }
                return PreprocessResult(success=False, error=json.dumps(details, ensure_ascii=False))

            plan = PreprocessPlan(
                strategy="compress_then_split",
                input_size_bytes=input_size,
                target_upload_bytes=target_upload_bytes,
                chunk_overlap_sec=self.chunk_overlap_sec,
                chunks=chunks,
            )

            logger.info(
                "audio_preprocess_decision %s",
                json.dumps(
                    {
                        "job_id": job_id,
                        "strategy": plan.strategy,
                        "chunk_count": len(chunks),
                        "chunk_sizes": [c.size_bytes for c in chunks],
                    },
                    ensure_ascii=False,
                ),
            )
            return PreprocessResult(success=True, plan=plan)

        except Exception as e:
            return PreprocessResult(success=False, error=str(e))
