import grpc
import time
import asyncio
from concurrent import futures
from typing import Optional

# 生成されたgRPCコードをインポート
from app.grpc_services.generated.analysis_pb2 import AnalysisResponse
from app.grpc_services.generated.analysis_pb2_grpc import AnalysisServiceServicer

# 共有コアサービスをインポート
from app.services.core.analysis_service import get_core_analysis_service
from app.core.logging import logger


class AnalysisService(AnalysisServiceServicer):
    """gRPC Analysis サービス実装 - 共有コアサービスを使用"""
    
    def __init__(self):
        """サービスを初期化"""
        self.core_service = None
        logger.info("AnalysisService の初期化が完了しました")
    
    async def _get_core_service(self):
        """コア分析サービスインスタンスを取得（遅延読み込み）"""
        if self.core_service is None:
            self.core_service = get_core_analysis_service()
            logger.debug("gRPC コア分析サービスインスタンスが作成されました")
        return self.core_service
    
    async def GetGeneralAnalysis(self, request, context):
        """ユーザーの総合ポートフォリオ分析を取得 - 共有コアサービスを使用"""
        try:
            logger.info(f"gRPC 分析リクエスト: user_id={request.user_id}")
            
            # コア分析サービスを取得
            core_service = await self._get_core_service()
            
            # 共有コア分析サービスを呼び出し
            result = await core_service.analyze_general_portfolio(
                request.user_id, 
                allow_empty_portfolio=False
            )
            
            logger.info(f"gRPC 分析完了: user_id={request.user_id}, success={result.success}")
            
            return AnalysisResponse(
                user_id=request.user_id,
                analysis_summary=result.analysis_summary,
                success=result.success,
                error_message=result.error_message or "",
                timestamp=result.timestamp
            )
            
        except Exception as e:
            logger.error(f"gRPC 分析エラー: user_id={request.user_id}, error={e}")
            return AnalysisResponse(
                user_id=request.user_id,
                success=False,
                error_message=str(e),
                timestamp=int(time.time())
            )


def _run_async_servicer_method(async_method, request, context):
    """非同期サーバーメソッドを実行するためのヘルパー関数"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(async_method(request, context))
    finally:
        loop.close()


class SyncAnalysisService(AnalysisServiceServicer):
    """同期的にラップされたgRPC Analysisサービス"""
    
    def __init__(self):
        self.async_service = AnalysisService()
    
    def GetGeneralAnalysis(self, request, context):
        """非同期メソッドを同期的に呼び出す"""
        return _run_async_servicer_method(
            self.async_service.GetGeneralAnalysis, 
            request, 
            context
        )
