#!/usr/bin/env python3
"""
共有ビジネスロジック層 テストスクリプト
コアサービス 機能 normally 動作するか 検証
"""
import asyncio
import sys
import os

# addproject根directory到Pythonpath
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.core.analysis_service import get_core_analysis_service
from app.services.core.recommendation_service import get_core_recommendation_service
from app.services.core.asset_service import get_core_asset_service
from app.core.logging import logger
from app.models.recommendations import RecommendationFeedbackRequest, RegenerationRequest


async def test_core_analysis_service():
    """コアanalysisサービス テスト"""
    logger.info("🧪 コアanalysisサービス テスト中...")
    
    try:
        core_service = get_core_analysis_service()
        
        # analysis機能 テスト（空 portfolio 許可）
        result = await core_service.analyze_general_portfolio(
            "test_user_123", 
            allow_empty_portfolio=True
        )
        
        logger.info(f"✅ コアanalysisサービス テスト結果: success={result.success}")
        if result.success:
            logger.info(f"   analysisサマリー 長さ: {len(result.analysis_summary)} string")
        else:
            logger.info(f"   エラーメッセージ: {result.error_message}")
            
        return result.success
        
    except Exception as e:
        logger.error(f"❌ コアanalysisサービス テスト failed: {e}")
        return False


async def test_core_recommendation_service():
    """コアrecommendationサービス テスト"""
    logger.info("🧪 コアrecommendationサービス テスト中...")
    
    try:
        core_service = get_core_recommendation_service()
        
        # ヘルスチェック テスト
        result = await core_service.health_check()
        
        logger.info(f"✅ コアrecommendationサービス ヘルスチェック: success={result.success}")
        if result.success:
            logger.info(f"   サービス状態: {result.data.get('status', 'unknown')}")
        else:
            logger.info(f"   エラーメッセージ: {result.error_message}")
            
        return result.success
        
    except Exception as e:
        logger.error(f"❌ コアrecommendationサービス テスト failed: {e}")
        return False


async def test_core_asset_service():
    """コアassetサービス テスト"""
    logger.info("🧪 コアassetサービス テスト中...")
    
    try:
        core_service = get_core_asset_service()
        
        # portfolio取得 テスト（空 許可）
        result = await core_service.get_user_portfolio(
            "test_user_123", 
            allow_empty=True
        )
        
        logger.info(f"✅ コアassetサービス テスト結果: success={result.success}")
        if result.success:
            if result.data:
                logger.info(f"   portfolio asset数: {len(result.data.assets) if result.data.assets else 0}")
            else:
                logger.info("   portfolio 空 す（normally）")
        else:
            logger.info(f"   エラーメッセージ: {result.error_message}")
            
        return result.success
        
    except Exception as e:
        logger.error(f"❌ コアassetサービス テスト failed: {e}")
        return False


async def test_service_integration():
    """サービス統合 テスト"""
    logger.info("🔗 サービス統合 テスト中...")
    
    try:
        # 複数 サービス 同時 動作するか テスト
        analysis_service = get_core_analysis_service()
        asset_service = get_core_asset_service()
        
        # 2つ サービス 同時 呼び出し
        analysis_task = analysis_service.analyze_general_portfolio("test_user_456", allow_empty_portfolio=True)
        asset_task = asset_service.get_user_portfolio("test_user_456", allow_empty=True)
        
        analysis_result, asset_result = await asyncio.gather(analysis_task, asset_task)
        
        integration_success = analysis_result.success and asset_result.success
        
        logger.info(f"✅ サービス統合テスト: success={integration_success}")
        logger.info(f"   analysisサービス: {analysis_result.success}")
        logger.info(f"   assetサービス: {asset_result.success}")
        
        return integration_success
        
    except Exception as e:
        logger.error(f"❌ サービス統合テスト failed: {e}")
        return False


async def main():
    """メインテスト関数"""
    logger.info("🚀 共有ビジネスロジック層 テスト 開始...")
    
    # すべて テスト execute
    tests = [
        ("コアanalysisサービス", test_core_analysis_service),
        ("コアrecommendationサービス", test_core_recommendation_service),
        ("コアassetサービス", test_core_asset_service),
        ("サービス統合", test_service_integration)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = await test_func()
            results.append((test_name, success))
        except Exception as e:
            logger.error(f"テスト {test_name}  例外 発生しました: {e}")
            results.append((test_name, False))
        
        # テスト間隔
        await asyncio.sleep(1)
    
    # テスト結果 summary
    logger.info("\n" + "="*50)
    logger.info("📊 テスト結果 summary:")
    logger.info("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ 合格" if success else "❌ failed"
        logger.info(f"{status} - {test_name}")
        if success:
            passed += 1
    
    logger.info("="*50)
    logger.info(f"合計: {passed}/{total} 件 テスト 合格しました")
    
    if passed == total:
        logger.info("🎉 すべて テスト 合格しました！共有ビジネスロジック層 normally 動作in progress。")
        return True
    else:
        logger.warning(f"⚠️ {total - passed} 件 テスト failed。関連するサービス設定 確認してください。")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("テスト user よってbreakされました")
        sys.exit(1)
    except Exception as e:
        logger.error(f"テストスクリプト 例外 終了しました: {e}")
        sys.exit(1)
