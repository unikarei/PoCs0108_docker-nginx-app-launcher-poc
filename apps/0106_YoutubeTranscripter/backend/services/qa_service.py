"""
QA Service
Provides question-answering over transcripts using OpenAI models
"""
from dataclasses import dataclass
from typing import Optional
import os
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)


@dataclass
class QaAnswerResult:
    success: bool
    answer: Optional[str] = None
    model: Optional[str] = None
    error: Optional[str] = None


class QaService:
    """Generate answers for user questions based on transcript text"""

    DEFAULT_MODEL = "gpt-4o-mini"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
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
                logger.info("OpenAI client initialized successfully for QA")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self.client = None

    def answer_question(self, transcript_text: str, question: str, model: str = DEFAULT_MODEL) -> QaAnswerResult:
        if not self.client:
            return QaAnswerResult(success=False, error="OpenAI API key not configured")

        try:
            logger.info(f"Processing QA with model {model}, transcript length: {len(transcript_text)}, question: {question[:50]}...")
            
            system_prompt = (
                "You are a helpful assistant for answering questions based on a transcript. "
                "Use the provided transcript strictly. If the answer is not in the transcript, say you cannot find it." 
                "Respond concisely in the same language as the transcript when possible."
            )

            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Transcript:\n{transcript_text}\n\nQuestion:\n{question}"},
                ],
                temperature=0.2,
            )

            answer = response.choices[0].message.content
            logger.info(f"QA completed successfully, answer length: {len(answer)}")
            return QaAnswerResult(success=True, answer=answer, model=model)
        except Exception as exc:
            logger.error(f"QA generation failed: {exc}", exc_info=True)
            return QaAnswerResult(success=False, error=str(exc))
