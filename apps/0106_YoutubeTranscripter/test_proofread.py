#!/usr/bin/env python3
"""
ProofRead機能のテストスクリプト
OpenAI APIとの接続を確認し、correction_serviceの動作をテスト
"""
import sys
import os

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, '/app')

from services.correction_service import CorrectionService
import logging

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_correction_service():
    """CorrectionServiceの動作テスト"""
    logger.info("=" * 60)
    logger.info("ProofRead機能テスト開始")
    logger.info("=" * 60)
    
    # APIキーの確認
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        logger.info(f"✓ OpenAI API Key found: {api_key[:10]}...")
    else:
        logger.error("✗ OpenAI API Key not found!")
        return False
    
    # CorrectionServiceの初期化
    logger.info("CorrectionServiceを初期化中...")
    try:
        service = CorrectionService()
        logger.info(f"✓ CorrectionService initialized: {service}")
        logger.info(f"✓ Client initialized: {service.client is not None}")
    except Exception as e:
        logger.error(f"✗ Failed to initialize CorrectionService: {e}")
        return False
    
    # テスト用テキスト
    test_text_ja = """
    これはテストです。
    おんせいにんしきのせいどをかくにんします。
    ぶんぽうのまちがいもなおします
    """
    
    # 校正テスト
    logger.info("=" * 60)
    logger.info("日本語テキストの校正テスト")
    logger.info("=" * 60)
    logger.info(f"入力テキスト:\n{test_text_ja}")
    
    try:
        logger.info("校正処理を実行中...")
        result = service.correct(
            transcript_text=test_text_ja,
            language="ja",
            model="gpt-4o-mini"
        )
        
        logger.info(f"結果のタイプ: {type(result)}")
        logger.info(f"Success: {result.success}")
        
        if result.success:
            logger.info("✓ 校正成功!")
            logger.info(f"校正後テキスト:\n{result.corrected_text}")
            logger.info(f"変更サマリー: {result.changes_summary}")
            logger.info(f"使用モデル: {result.model}")
            return True
        else:
            logger.error(f"✗ 校正失敗: {result.error}")
            return False
            
    except Exception as e:
        logger.error(f"✗ Exception during correction: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = test_correction_service()
    logger.info("=" * 60)
    if success:
        logger.info("✓ テスト成功!")
        sys.exit(0)
    else:
        logger.error("✗ テスト失敗")
        sys.exit(1)
