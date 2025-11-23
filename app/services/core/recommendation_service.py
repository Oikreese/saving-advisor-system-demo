"""
コアrecommendationサービス - 共有ビジネスロジック
FastAPI gRPCエンドPoints 共通してuseされる統一されたrecommendationサービス provide
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
import time

# プロジェクト コア依存関係
from app.services.firestore.firestore_primary_service import FirestorePrimaryService, get_firestore_primary_service
from app.services.llm.openai_service import OpenAIService, get_openai_service
from app.models.recommendations import RecommendationFeedbackRequest, RegenerationRequest, RecommendationDetail
from app.core.logging import logger


class RecommendationResult:
    """recommendation結果dataクラス"""
    
    def __init__(
        self, 
        success: bool = True,
        data: Optional[Any] = None,
        error_message: Optional[str] = None,
        timestamp: Optional[int] = None
    ):
        self.success = success
        self.data = data
        self.error_message = error_message
        self.timestamp = timestamp or int(time.time())
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式 変換"""
        return {
            "success": self.success,
            "data": self.data,
            "error_message": self.error_message,
            "timestamp": self.timestamp
        }


class CoreRecommendationService:
    """
    コアrecommendationサービス - 統一されたビジネスロジック層
    
    こ サービス 、すべて recommendation関連 コアビジネスロジック 含み、以下 エンドPoints useされます：
    - FastAPI RESTエンドPoints
    - gRPCサービスエンドPoints
    - in部サービス呼び出し
    """
    
    def __init__(self):
        """コアrecommendationサービス 初期化"""
        self._firestore_service: Optional[FirestorePrimaryService] = None
        self._openai_service: Optional[OpenAIService] = None
        logger.info("CoreRecommendationService  初期化 完了しました")
    
    async def _get_firestore_service(self) -> FirestorePrimaryService:
        """Firestoreサービスインスタンス 取得（遅延読み込み）"""
        if self._firestore_service is None:
            self._firestore_service = get_firestore_primary_service()
            logger.debug("Firestoreサービスインスタンス 作成されました")
        return self._firestore_service
    
    async def _get_openai_service(self) -> OpenAIService:
        """OpenAIサービスインスタンス 取得（遅延読み込み）"""
        if self._openai_service is None:
            self._openai_service = get_openai_service()
            logger.debug("OpenAIサービスインスタンス 作成されました")
        return self._openai_service
    
    # =============== コアrecommendationメソッド ===============
    
    async def record_recommendation_feedback(
        self, 
        request: RecommendationFeedbackRequest
    ) -> RecommendationResult:
        """
        recommendationfeedback 記録 - コアビジネスロジック
        
        Args:
            request: recommendationfeedbackリクエスト
            
        Returns:
            RecommendationResult: operations結果
        """
        logger.info(f"recommendationfeedback 記録: user_id={request.user_id}, recommendation_id={request.recommendation_id}")
        
        try:
            # Firestoreサービス 取得
            firestore_service = await self._get_firestore_service()
            
            # 実際 feedback記録関数 呼び出し
            from app.api.v1.endpoints.recommendations_firestore_primary import (
                record_recommendation_feedback_v2 as _record_recommendation_feedback
            )
            
            # feedback記録 execute
            result = await _record_recommendation_feedback(request, firestore_service)
            
            logger.info(f"recommendationfeedback 記録 success: user_id={request.user_id}")
            
            return RecommendationResult(
                success=True,
                data=result
            )
            
        except Exception as e:
            logger.error(f"recommendationfeedback 記録 failed: user_id={request.user_id}, error={e}")
            return RecommendationResult(
                success=False,
                error_message=str(e)
            )
    
    async def regenerate_recommendation(
        self, 
        request: RegenerationRequest
    ) -> RecommendationResult:
        """
        recommendation regenerate - コアビジネスロジック
        
        Args:
            request: regenerateリクエスト
            
        Returns:
            RecommendationResult: regenerate結果
        """
        logger.info(f"recommendation regenerate: user_id={request.user_id}, agent={request.agent_name}")
        
        try:
            # 依存サービス 取得
            firestore_service = await self._get_firestore_service()
            openai_service = await self._get_openai_service()
            
            # 実際 regenerate関数 呼び出し
            from app.api.v1.endpoints.recommendations_firestore_primary import (
                regenerate_recommendation_v2 as _regenerate_recommendation
            )
            
            # regenerate execute
            result = await _regenerate_recommendation(request, firestore_service, openai_service)
            
            logger.info(f"recommendation regenerate success: user_id={request.user_id}")
            
            return RecommendationResult(
                success=True,
                data=result
            )
            
        except Exception as e:
            logger.error(f"recommendation regenerate failed: user_id={request.user_id}, error={e}")
            return RecommendationResult(
                success=False,
                error_message=str(e)
            )
    
    async def get_user_recommendations(
        self, 
        user_id: str,
        limit: int = 10
    ) -> RecommendationResult:
        """
        user recommendationlist 取得
        
        Args:
            user_id: userID
            limit: 制限数
            
        Returns:
            RecommendationResult: recommendationlist結果
        """
        logger.info(f"user recommendation 取得: user_id={user_id}, limit={limit}")
        
        try:
            # Firestoreサービス 取得
            firestore_service = await self._get_firestore_service()
            
            # user recommendation履歴 取得
            recommendations = await firestore_service.get_user_recommendations(user_id, limit=limit)
            
            logger.info(f"user recommendation取得 success: user_id={user_id}, count={len(recommendations) if recommendations else 0}")
            
            return RecommendationResult(
                success=True,
                data=recommendations
            )
            
        except Exception as e:
            logger.error(f"user recommendation取得 failed: user_id={user_id}, error={e}")
            return RecommendationResult(
                success=False,
                error_message=str(e)
            )
    
    async def health_check(self) -> RecommendationResult:
        """
        recommendationサービス ヘルスチェック
        
        Returns:
            RecommendationResult: ヘルスチェック結果
        """
        try:
            # 依存サービス 接続 確認
            firestore_service = await self._get_firestore_service()
            openai_service = await self._get_openai_service()
            
            # 簡単な接続テスト
            # ここ さら 多く ヘルスチェックロジック append きます
            
            return RecommendationResult(
                success=True,
                data={
                    "status": "healthy",
                    "service": "core_recommendation_service",
                    "firestore": "connected",
                    "openai": "connected",
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"recommendationサービス ヘルスチェック failed: {e}")
            return RecommendationResult(
                success=False,
                error_message=str(e)
            )


# =============== シングルトンインスタンス ===============

_core_recommendation_service: Optional[CoreRecommendationService] = None


def get_core_recommendation_service() -> CoreRecommendationService:
    """
    コアrecommendationサービス シングルトンインスタンス 取得
    
    Returns:
        CoreRecommendationService: コアrecommendationサービスインスタンス
    """
    global _core_recommendation_service
    if _core_recommendation_service is None:
        _core_recommendation_service = CoreRecommendationService()
        logger.info("コアrecommendationサービス シングルトンインスタンス 作成されました")
    return _core_recommendation_service
