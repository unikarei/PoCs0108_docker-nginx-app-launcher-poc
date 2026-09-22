"""Generate detailed, chapter-based key points from a transcript."""

from dataclasses import dataclass
import logging
import os
from typing import Optional

from openai import OpenAI

logger = logging.getLogger(__name__)


DEFAULT_KEY_POINTS_PROMPT = """詳細要点抽出プロンプト

以下のTranscriptを、章ごとに題目を付けて整理してください。

単なる短い要約ではなく、**内容を後からTranscriptを読み直さなくても把握できるレベルの「詳細な要点抽出」**を行ってください。

## 出力ルール

1. 内容の流れに沿って適切な章に分割し、各章に分かりやすい題目を付ける。
2. **各章について、重要事項を10〜20項目程度を目安に詳しく列記する。**
   - 内容の少ない章は無理に10項目に増やす必要はない。
   - 内容の多い章は20項目を超えてもよい。
   - 全体として、通常の簡潔な要約より**約3倍程度多くの情報を残す**こと。
3. 以下は省略せず、可能な限り独立した要点として残す。
   - 話者の主要な主張
   - その主張に至る理由・背景
   - 根拠として挙げている内容
   - 具体例
   - エピソード
   - 人物名・組織名・地名
   - 年代・数字・金額
   - 原因と結果の関係
   - 比較・対比
   - 話者が特に強調している点
   - 結論や今後の予測
   - 前後の話をつなぐ重要な補足説明
4. **複数の異なる論点を1つの短い箇条書きにまとめすぎないこと。**
   例えば、

   「Aが起き、その背景にはBがあり、その結果Cになった」

   という説明がある場合は、必要に応じて
   - Aという出来事
   - Aが起きた背景としてBを説明
   - その結果としてCが生じたと主張
   のように分ける。
5. 一つ一つの要点は、単語や短いフレーズだけではなく、**原則1〜3文程度で内容が理解できるように記述する。**
6. Transcript内で繰り返されているだけの内容は統合してよいが、**意味やニュアンスの異なる発言を安易に同一項目へ統合しない。**
7. Transcriptに登場する情報を優先し、勝手な推測や外部情報を付け加えない。
8. 話者の主張、推測、都市伝説、意見などについては、それを客観的事実として断定せず、
   - 「話者は〜と主張している」
   - 「動画では〜と説明している」
   - 「〜ではないかという説を紹介している」
   のように、**Transcript内の主張であることが分かる表現**にする。
9. 最後に情報量を自己チェックし、
   **「短くまとめすぎていないか」「重要な理由・具体例・背景を落としていないか」**
   を確認してから出力する。

## 出力形式

### 1. 章タイトル

- 要点1
- 要点2
- 要点3
- …
- 必要に応じて10〜20項目以上
- …
- 必要に応じて10〜20項目以上

### 2. 章タイトル

- 要点1
- 要点2
- 要点3
- …

この形式でTranscript全体を最後まで処理してください。"""


@dataclass
class KeyPointsResult:
    """Result returned by the extraction service without raising API errors."""

    success: bool
    text: Optional[str] = None
    model: Optional[str] = None
    error: Optional[str] = None


class KeyPointsService:
    """Call the configured OpenAI chat model for detailed key-point extraction."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = None
        if self.api_key:
            try:
                self.client = OpenAI(api_key=self.api_key, timeout=180.0, max_retries=3)
            except Exception as exc:
                logger.error("Failed to initialize key-point OpenAI client: %s", exc)

    def extract(self, transcript_text: str, prompt: str, model: str) -> KeyPointsResult:
        """Extract detailed points using only the supplied transcript."""
        if not self.client:
            return KeyPointsResult(success=False, model=model, error="OpenAI API key not configured")

        try:
            request_options = {
                "model": model,
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Transcript:\n{transcript_text}"},
                ],
            }
            if model != "gpt-5-mini":
                request_options["temperature"] = 0.2

            response = self.client.chat.completions.create(**request_options)
            text = response.choices[0].message.content or ""
            if not text.strip():
                return KeyPointsResult(success=False, model=model, error="The LLM returned an empty result")
            return KeyPointsResult(success=True, text=text, model=model)
        except Exception as exc:
            logger.error("Key-point extraction failed: %s", exc, exc_info=True)
            return KeyPointsResult(success=False, model=model, error=str(exc))
