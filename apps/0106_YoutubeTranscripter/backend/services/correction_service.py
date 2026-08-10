"""
Correction Service
Handles transcript correction using OpenAI GPT-4o-mini
"""
from openai import OpenAI
import os
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List
import logging
import difflib

logger = logging.getLogger(__name__)


@dataclass
class CorrectionResult:
    """
    Result of correction operation
    """
    success: bool
    corrected_text: Optional[str] = None
    original_text: Optional[str] = None
    changes_summary: Optional[str] = None
    model: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __contains__(self, key: object) -> bool:
        return isinstance(key, str) and hasattr(self, key)


class CorrectionService:
    """
    Service for correcting transcripts using OpenAI GPT-4o-mini
    """
    
    # Default model
    DEFAULT_MODEL = "gpt-4o-mini"
    
    # Token limits (conservative estimate for GPT-4o-mini)
    MAX_TOKENS_PER_REQUEST = 3000
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize correction service
        
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
                logger.info("OpenAI client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self.client = None
    
    def _generate_correction_prompt(self, language: str) -> str:
        """
        Generate correction prompt based on language
        
        Args:
            language: Target language (ja or en)
            
        Returns:
            System prompt for correction
        """
        if language == "ja":
            return """あなたは日本語の文字起こし校正の専門家です。
以下のタスクを実行してください：

1. 誤変換の修正（音声認識の誤りを修正）
2. 適切な句読点の配置
3. 段落の整形（読みやすさの向上）
4. 文法エラーの修正
5. 不自然な表現の改善

元のテキストの意味を変えないように注意し、必要な修正のみを行ってください。
校正後のテキストのみを返してください。説明は不要です。"""
        
        elif language == "en":
            return """You are an expert in English transcription correction.
Please perform the following tasks:

1. Fix transcription errors (correct speech recognition mistakes)
2. Add proper punctuation
3. Format paragraphs for readability
4. Correct grammar errors
5. Improve unnatural expressions

Be careful not to change the original meaning, and only make necessary corrections.
Return only the corrected text without explanations."""
        
        else:
            return """You are an expert in transcription correction.
Please correct any errors in punctuation, grammar, and formatting while preserving the original meaning.
Return only the corrected text without explanations."""
    
    def _split_text(self, text: str, max_tokens: int = MAX_TOKENS_PER_REQUEST) -> List[str]:
        """
        Split text into chunks for token limit handling
        
        Args:
            text: Text to split
            max_tokens: Maximum tokens per chunk (approximate)
            
        Returns:
            List of text chunks
        """
        # Simple splitting by approximate character count
        # ~4 characters per token for Japanese, ~5 for English
        chars_per_token = 4
        max_chars = max_tokens * chars_per_token
        
        if len(text) <= max_chars:
            return [text]
        
        # Split by paragraphs first
        paragraphs = text.split('\n\n')
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for para in paragraphs:
            para_length = len(para)
            
            if current_length + para_length > max_chars:
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = [para]
                    current_length = para_length
                else:
                    # Single paragraph too long, split by sentences
                    sentences = para.split('。')
                    for sentence in sentences:
                        if sentence:
                            chunks.append(sentence + '。')
            else:
                current_chunk.append(para)
                current_length += para_length
        
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks
    
    def _calculate_changes_summary(self, original: str, corrected: str) -> str:
        """
        Calculate summary of changes made
        
        Args:
            original: Original text
            corrected: Corrected text
            
        Returns:
            Summary of changes
        """
        # Calculate diff statistics
        differ = difflib.Differ()
        diff = list(differ.compare(original.split(), corrected.split()))
        
        additions = sum(1 for d in diff if d.startswith('+ '))
        deletions = sum(1 for d in diff if d.startswith('- '))
        
        if additions == 0 and deletions == 0:
            return "No changes made"
        
        return f"Modified: {additions} additions, {deletions} deletions"
    
    def correct(
        self,
        transcript_text: str,
        language: str,
        model: str = DEFAULT_MODEL
    ) -> Dict[str, Any]:
        """
        Correct transcript text using GPT-4o-mini
        
        Args:
            transcript_text: Original transcript text
            language: Language code (ja, en)
            model: GPT model to use
            
        Returns:
            Dict with correction result
        """
        if not self.client:
            logger.error("OpenAI client not initialized")
            return CorrectionResult(
                success=False,
                error="OpenAI API key not configured"
            )
        
        try:
            # Generate correction prompt
            system_prompt = self._generate_correction_prompt(language)
            
            # Handle long text by splitting
            chunks = self._split_text(transcript_text)
            
            if len(chunks) == 1:
                # Single request
                logger.info(f"Correcting text with {model} (length: {len(transcript_text)} chars)")
                
                try:
                    response = self.client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": transcript_text}
                        ],
                        temperature=0.3  # Lower temperature for more consistent corrections
                    )
                    
                    corrected_text = response.choices[0].message.content
                    logger.info(f"Correction API call successful (output: {len(corrected_text)} chars)")
                    
                except Exception as api_error:
                    logger.error(f"OpenAI API call failed: {api_error}", exc_info=True)
                    raise
                
            else:
                # Multiple requests for long text
                logger.info(f"Correcting long text in {len(chunks)} chunks (total: {len(transcript_text)} chars)")
                
                corrected_chunks = []
                for i, chunk in enumerate(chunks):
                    logger.info(f"Correcting chunk {i+1}/{len(chunks)} (length: {len(chunk)} chars)")
                    
                    try:
                        response = self.client.chat.completions.create(
                            model=model,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": chunk}
                            ],
                            temperature=0.3
                        )
                        
                        chunk_result = response.choices[0].message.content
                        corrected_chunks.append(chunk_result)
                        logger.info(f"Chunk {i+1}/{len(chunks)} completed (output: {len(chunk_result)} chars)")
                        
                    except Exception as api_error:
                        logger.error(f"OpenAI API call failed for chunk {i+1}: {api_error}", exc_info=True)
                        raise
                
                corrected_text = '\n\n'.join(corrected_chunks)
                logger.info(f"All chunks corrected (total output: {len(corrected_text)} chars)")
            
            # Calculate changes summary
            changes_summary = self._calculate_changes_summary(transcript_text, corrected_text)
            
            result = CorrectionResult(
                success=True,
                corrected_text=corrected_text,
                original_text=transcript_text,
                changes_summary=changes_summary,
                model=model,
            )

            logger.info("Correction completed successfully")
            return result
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Correction error: {e}", exc_info=True)
            
            # Provide more specific error messages
            if "connection" in error_msg.lower() or "timeout" in error_msg.lower():
                error_detail = f"OpenAI API connection failed: {error_msg}"
            elif "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
                error_detail = f"OpenAI API authentication failed: {error_msg}"
            elif "rate_limit" in error_msg.lower():
                error_detail = f"OpenAI API rate limit exceeded: {error_msg}"
            else:
                error_detail = f"Correction failed: {error_msg}"
                
            return CorrectionResult(
                success=False,
                error=error_detail
            )

    def correct_transcript(self, transcript: str, language: str, model: str = DEFAULT_MODEL) -> Dict[str, Any]:
        """Alias kept for backward compatibility with worker"""
        return self.correct(transcript_text=transcript, language=language, model=model)
